"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface SourceViewerProps {
  url: string | null;
  evidenceId: string | null;
  onClose: () => void;
}

export function SourceViewer({ url, evidenceId, onClose }: SourceViewerProps) {
  if (!url) return null;

  const isDev = process.env.NODE_ENV === "development";
  const baseUrl = isDev ? "http://127.0.0.1:8000" : "";
  const proxyUrl = `${baseUrl}/api/py/pdf?url=${encodeURIComponent(url)}`;

  return (
    <Dialog open={!!url} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-4 py-3 border-b border-[#E2E4E9] flex-shrink-0">
          <DialogTitle className="text-sm font-medium flex items-center gap-2">
            <span className="text-muted-foreground">View Source</span>
            <span className="font-mono text-xs text-blue-600">{evidenceId}</span>
          </DialogTitle>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline truncate block"
          >
            {url} &#8599;
          </a>
        </DialogHeader>

        <div className="flex-1 min-h-0">
          <iframe
            src={proxyUrl}
            className="w-full h-full border-0"
            title="Source viewer"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
