"""
File upload components for XLS, PPT, PDF.
"""
from fasthtml.common import *


def UploadZone():
    return Div(
        H2("Upload Documents", cls="text-xl font-bold text-gray-800 mb-4"),
        P("Upload CIMs, financial models, pitch decks, or any M&A-related documents for AI analysis.",
          cls="text-sm text-gray-600 mb-6"),
        Form(
            Div(
                Div(
                    P("Upload", cls="text-3xl mb-2"),
                    P("Drag & drop or click to upload", cls="text-sm font-medium text-gray-600"),
                    P("XLS, XLSX, PPT, PPTX, PDF (max 50MB)", cls="text-xs text-gray-400 mt-1"),
                    cls="text-center",
                ),
                Div(
                    Span("XLS", cls="bg-green-100 text-green-700 text-xs font-bold px-2 py-1 rounded"),
                    Span("PPT", cls="bg-orange-100 text-orange-700 text-xs font-bold px-2 py-1 rounded"),
                    Span("PDF", cls="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded"),
                    cls="flex gap-2 justify-center mt-3",
                ),
                Input(type="file", name="file", accept=".xlsx,.xls,.pptx,.ppt,.pdf",
                      cls="absolute inset-0 w-full h-full opacity-0 cursor-pointer"),
                cls="relative border-2 border-dashed border-gray-300 rounded-xl p-8 hover:border-blue-400 hover:bg-blue-50 transition-colors cursor-pointer",
            ),
            Button("Upload & Analyze", type="submit",
                   cls="w-full mt-4 bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"),
            hx_post="/upload",
            hx_target="#upload-results",
            hx_encoding="multipart/form-data",
            hx_indicator="#upload-spinner",
        ),
        Div(
            Div(cls="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"),
            P("Parsing document...", cls="text-sm text-gray-500 ml-2"),
            id="upload-spinner",
            cls="htmx-indicator flex items-center justify-center mt-4",
        ),
        Div(id="upload-results", cls="mt-6"),
        cls="max-w-xl mx-auto",
    )


def UploadResult(parsed: dict):
    """Display parsed document results."""
    summary = parsed.get("summary", "Document parsed")
    doc_type = parsed.get("type", "unknown")
    filename = parsed.get("filename", "")

    type_colors = {"xlsx": "bg-green-100 text-green-700", "pptx": "bg-orange-100 text-orange-700", "pdf": "bg-red-100 text-red-700"}
    t_cls = type_colors.get(doc_type, "bg-gray-100 text-gray-700")

    return Div(
        Div(
            Span(doc_type.upper(), cls=f"text-xs font-bold px-2 py-1 rounded {t_cls}"),
            Span(filename, cls="text-sm font-medium text-gray-800"),
            cls="flex items-center gap-2",
        ),
        P(summary, cls="text-sm text-gray-600 mt-2"),
        Div(
            Button("Feed to Scoring Agent", hx_post=f"/analyze-doc/{filename}", hx_target="#main-content",
                   cls="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"),
            Button("View Contents", hx_get=f"/doc-preview/{filename}", hx_target="#doc-preview",
                   cls="text-sm bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"),
            cls="flex gap-2 mt-3",
        ),
        Div(id="doc-preview", cls="mt-4"),
        cls="bg-white rounded-lg p-4 border border-gray-200",
    )
