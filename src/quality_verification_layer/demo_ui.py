"""Rich terminal UI for the quality verification demo results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

console = Console()

STATUS_COLORS = {
    "verified": "bold green",
    "verified_with_gaps": "bold yellow",
    "failed_hard_requirements": "bold red",
    "insufficient_evidence": "dim",
    "processing_error": "bold red",
}

CONF_COLORS = {"high": "green", "medium": "yellow", "low": "dim"}

VER_ICONS = {
    "pass": ("[bold green]+[/]", "green"),
    "fail": ("[bold red]X[/]", "red"),
    "unknown": ("[bold yellow]?[/]", "yellow"),
    "partial": ("[bold cyan]~[/]", "cyan"),
}


def show_layer1_results(requirements: list, ingredient_name: str):
    """Display Layer 1 requirements in a table."""
    table = Table(
        title=f"Layer 1: Requirements for {ingredient_name}",
        box=box.ROUNDED,
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Field", style="bold")
    table.add_column("Rule", width=12)
    table.add_column("Constraint", width=25)
    table.add_column("Priority", width=8)
    table.add_column("Source", style="dim", width=15)

    for i, r in enumerate(requirements, 1):
        rule_type = r.rule_type if isinstance(r.rule_type, str) else r.rule_type.value
        priority = r.priority if isinstance(r.priority, str) else r.priority.value
        p_style = "bold red" if priority == "hard" else "yellow"

        constraint = ""
        if rule_type == "range" and r.min_value is not None:
            constraint = f"{r.min_value} - {r.max_value} {r.unit or ''}"
        elif rule_type == "minimum" and r.min_value is not None:
            constraint = f">= {r.min_value} {r.unit or ''}"
        elif rule_type == "maximum" and r.max_value is not None:
            constraint = f"<= {r.max_value} {r.unit or ''}"
        elif rule_type == "enum_match" and r.allowed_values:
            constraint = ", ".join(r.allowed_values[:4])
            if len(r.allowed_values) > 4:
                constraint += "..."
        elif rule_type == "boolean_required":
            constraint = f"required = {r.required}"

        table.add_row(
            str(i),
            r.field_name,
            rule_type,
            constraint,
            Text(priority, style=p_style),
            r.source_reference or "",
        )

    console.print(table)
    console.print()


def show_layer2_results(competitors: list, db_suppliers: list, ingredient_name: str):
    """Display Layer 2 competitor discovery results."""
    table = Table(
        title=f"Layer 2: Suppliers for {ingredient_name}",
        box=box.ROUNDED,
        title_style="bold cyan",
    )
    table.add_column("Source", width=8)
    table.add_column("Supplier", style="bold")
    table.add_column("Country", width=8)
    table.add_column("Confidence", width=12)
    table.add_column("URLs", width=5, justify="right")

    for s in db_suppliers:
        table.add_row(
            Text("DB", style="blue"),
            s.supplier.supplier_name,
            s.supplier.country or "?",
            "-",
            str(len(s.source_urls)),
        )

    for s in competitors:
        conf = s.candidate_confidence if isinstance(s.candidate_confidence, str) else s.candidate_confidence.value
        conf_style = CONF_COLORS.get(conf, "dim")
        table.add_row(
            Text("L2", style="magenta"),
            s.supplier.supplier_name,
            s.supplier.country or "?",
            Text(conf, style=conf_style),
            str(len(s.source_urls)),
        )

    console.print(table)
    console.print()


def show_layer3_results(output, requirements: list, names: dict[str, str] = None):
    """Display Layer 3 verification results for all suppliers."""
    for sa in output.supplier_assessments:
        _show_supplier_assessment(sa, names)

    console.print()


def _show_supplier_assessment(sa, names: dict[str, str] = None):
    """Display one supplier's verification result as a panel."""
    status = sa.overall_status
    status_style = STATUS_COLORS.get(status, "dim")
    conf = sa.overall_evidence_confidence
    conf_style = CONF_COLORS.get(conf, "dim")

    # Evidence summary
    retrieved = sum(1 for e in sa.evidence_items if e.status == "retrieved")
    types: dict = {}
    for e in sa.evidence_items:
        if e.status == "retrieved":
            t = e.source_type
            types[t] = types.get(t, 0) + 1
    type_str = ", ".join(f"{v}x {k}" for k, v in types.items()) if types else "none"

    # Verification table
    ver_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    ver_table.add_column("", width=3)
    ver_table.add_column("Field", width=22)
    ver_table.add_column("Result", width=55)

    for vr in sa.verification_results:
        st = vr.status if isinstance(vr.status, str) else vr.status.value
        icon, color = VER_ICONS.get(st, ("[?]", "dim"))
        reason = vr.reason if len(vr.reason) <= 55 else vr.reason[:52] + "..."
        ver_table.add_row(icon, vr.field_name, Text(reason, style=color))

    # Coverage line
    cov = sa.coverage_summary
    cov_text = (
        f"Hard: [green]{cov.hard_pass}P[/] [red]{cov.hard_fail}F[/] [yellow]{cov.hard_unknown}U[/]  "
        f"Soft: [green]{cov.soft_pass}P[/] [red]{cov.soft_fail}F[/] [yellow]{cov.soft_unknown}U[/]"
    )

    # Build panel content
    content = Text()
    content.append(f"Status: ", style="dim")
    content.append(f"{status}\n", style=status_style)
    content.append(f"Confidence: ", style="dim")
    content.append(f"{conf}\n", style=conf_style)
    content.append(f"Evidence: {retrieved}/{len(sa.evidence_items)} retrieved ({type_str})\n", style="dim")
    content.append(f"Extracted: {len(sa.extracted_attributes)} fields\n", style="dim")

    display_name = (names or {}).get(sa.supplier_id, sa.supplier_id)
    console.print(Panel(
        content,
        title=f"[bold]{display_name}[/] [dim]({sa.supplier_id})[/]",
        border_style="blue",
        width=85,
    ))
    console.print(f"  Coverage: {cov_text}")
    console.print(ver_table)

    if sa.notes:
        for n in sa.notes[:2]:
            note = n if len(n) <= 75 else n[:72] + "..."
            console.print(f"  [dim italic]{note}[/]")

    console.print()


def show_final_ranking(ranked: list, ingredient_name: str, names: dict[str, str] = None):
    """Display the final supplier ranking table."""
    table = Table(
        title=f"Supplier Quality Ranking: {ingredient_name}",
        box=box.HEAVY_HEAD,
        title_style="bold white on blue",
        show_lines=True,
        width=85,
    )
    table.add_column("#", width=3, justify="center", style="bold")
    table.add_column("Supplier", min_width=22, style="bold")
    table.add_column("Score", width=7, justify="center")
    table.add_column("Hard", width=7, justify="center")
    table.add_column("Soft", width=7, justify="center")
    table.add_column("Fails", width=5, justify="center")
    table.add_column("?", width=4, justify="center")
    table.add_column("Status", min_width=14)

    if not ranked:
        table.add_row("—", "[dim]No suppliers with extracted data[/]", "", "", "", "", "", "")
        console.print(table)
        console.print()
        return

    for i, (sa, score, d) in enumerate(ranked, 1):
        status = sa.overall_status
        status_style = STATUS_COLORS.get(status, "dim")

        if score >= 0.5:
            score_style = "bold green"
        elif score >= 0.25:
            score_style = "bold yellow"
        else:
            score_style = "dim"

        fail_style = "bold red" if d["fails"] > 0 else "green"
        unk_style = "yellow" if d["unknowns"] > 5 else "dim"

        name = (names or {}).get(sa.supplier_id, sa.supplier_id)
        if len(name) > 25:
            name = name[:22] + "..."

        table.add_row(
            f"#{i}",
            name,
            Text(f"{score:.0%}", style=score_style),
            d["hard"],
            d["soft"],
            Text(str(d["fails"]), style=fail_style),
            Text(str(d["unknowns"]), style=unk_style),
            Text(status, style=status_style),
        )

    console.print(table)
    console.print(f"  [dim]Score = (hard pass rate × 70%) + (soft pass rate × 30%). Partial counts as pass.[/]")
    console.print()


def show_header():
    console.print()
    console.print(Panel(
        "[bold]Agnes Quality Verification Layer[/]\n"
        "[dim]End-to-end demo: Layer 1 (Requirements) + Layer 2 (Competitors) + Layer 3 (Verification)[/]",
        style="cyan",
        width=85,
    ))
    console.print()


def show_ingredient_header(label: str, n_db: int, n_comp: int, idx: int, total: int):
    console.rule(f"[bold white] [{idx}/{total}] {label} [/]", style="white")
    console.print(f"  [dim]Suppliers: {n_db} from DB + {n_comp} competitors = {n_db + n_comp} total[/]")
    console.print()


def show_footer(total_time: float, total_shown: int, total_all: int, demo_output=None):
    console.print()
    summary = (
        f"[bold]Assessed {total_all} suppliers, "
        f"showing {total_shown} with usable evidence[/]\n"
        f"[dim]Total time: {total_time:.0f}s[/]"
    )
    if demo_output and demo_output.exists():
        pdf_count = sum(1 for _ in demo_output.rglob("*.pdf"))
        if pdf_count:
            summary += f"\n[green]PDFs saved to: {demo_output}[/]"

    console.print(Panel(summary, style="cyan", title="Done", width=85))
    console.print()
