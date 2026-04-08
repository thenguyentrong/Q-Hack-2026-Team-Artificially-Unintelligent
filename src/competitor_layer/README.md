# Agnes Competitor Layer

Supplier discovery module for CPG ingredient sourcing. Given an ingredient, finds plausible alternative supplier candidates and returns a structured candidate set for downstream quality verification.

Part of the Agnes decision-support system. See [`agnes_competitor_layer_spec.md`](../agnes_competitor_layer_spec.md) for the full specification.

## Install

```bash
pip install -e .
```

## Configure

```bash
cp .env.example .env
# Edit .env with your values
```

## Usage

```bash
competitor-layer examples/input_ascorbic_acid.json
```

## Tests

```bash
pip install pytest
pytest tests/ -v
```
