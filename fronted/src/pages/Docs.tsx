import React, {useMemo, useState} from "react";

/**
 * Beautiful, zero-deps docs page for your FastAPI endpoints.
 * Tailwind-only styling, safe string rendering (prevents "Unresolved variable or type" from TS/JSX inference).
 *
 * Endpoints:
 *  - POST http://localhost:8000/v1/ocr
 *  - POST http://localhost:8000/v1/correct
 *  - POST http://localhost:8000/v1/chat
 */

const LANGS = ["curl", "javascript", "python", "java"] as const;
type Lang = typeof LANGS[number];

function CopyButton({text, small = false}: { text: string; small?: boolean }) {
    const [copied, setCopied] = useState(false);

    async function onCopy() {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
        } catch {
        }
    }

    return (
        <button
            onClick={onCopy}
            className={[
                "inline-flex items-center justify-center rounded-xl font-semibold transition",
                small ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm",
                copied
                    ? "bg-emerald-600 text-white"
                    : "bg-white text-gray-700 border border-gray-200 hover:border-emerald-500 hover:text-emerald-700"
            ].join(" ")}
            aria-label="Copy to clipboard"
            title="Copy"
        >
            {copied ? "✓ Copied" : "⧉ Copy"}
        </button>
    );
}

function CodeBlock({language, code}: { language: Lang; code: string }) {
    // Escape to ensure JSX never tries to evaluate code; avoids "Unresolved variable or type …" noise.
    const safe = useMemo(
        () => code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"),
        [code]
    );

    return (
        <div className="relative">
            <div className="absolute left-4 top-3 text-[11px] uppercase tracking-wider text-gray-400">
                {language}
            </div>
            <div className="absolute right-3 top-3">
                <CopyButton text={code} small/>
            </div>
            <pre
                className="overflow-auto rounded-2xl border border-gray-200 bg-[#0b1020] text-gray-100 p-4 pt-7 shadow-inner text-[13px] leading-6">
        <code
            className="whitespace-pre"
            dangerouslySetInnerHTML={{__html: safe}}
        />
      </pre>
        </div>
    );
}

function CodeTabs({snippets}: { snippets: Record<Lang, string> }) {
    const [tab, setTab] = useState<Lang>(LANGS[0]);

    return (
        <div className="rounded-2xl border border-gray-200 overflow-hidden bg-white">
            <div className="flex flex-wrap gap-2 border-b bg-gray-50/60 px-3 py-2">
                {LANGS.map((l) => (
                    <button
                        key={l}
                        onClick={() => setTab(l)}
                        className={[
                            "px-3 py-1.5 rounded-lg text-sm font-semibold transition",
                            tab === l ? "bg-emerald-600 text-white" : "text-gray-700 hover:bg-emerald-50"
                        ].join(" ")}
                    >
                        {l}
                    </button>
                ))}
            </div>
            <div className="p-4">
                <CodeBlock language={tab} code={snippets[tab]}/>
            </div>
        </div>
    );
}

/* =========================
   Snippets (safe strings)
   ========================= */

const ocrCurl = `curl -X 'POST' \\
  'http://localhost:8000/v1/ocr' \\
  -H 'accept: application/json' \\
  -H 'x-api-key: YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{
  "fileName": "sample.png",
  "fileBase64": "<BASE64_WITHOUT_PREFIX>",
  "language": "en",
  "documentType": "INVOICE",
  "provider": "mistral-ocr-latest",
  "prompt": "Return Markdown with tables when present."
}'`;

const ocrJS = `async function runOCR() {
  const res = await fetch("http://localhost:8000/v1/ocr", {
    method: "POST",
    headers: {
      "accept": "application/json",
      "x-api-key": "YOUR_API_KEY",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      fileName: "sample.png",
      fileBase64: "<BASE64_WITHOUT_PREFIX>",
      language: "en",
      documentType: "INVOICE",
      provider: "mistral-ocr-latest",
      prompt: "Return Markdown with tables when present."
    })
  });
  const data = await res.json();
  console.log(data);
}
runOCR();`;

const ocrPy = `import requests

url = "http://localhost:8000/v1/ocr"
payload = {
  "fileName": "sample.png",
  "fileBase64": "<BASE64_WITHOUT_PREFIX>",
  "language": "en",
  "documentType": "INVOICE",
  "provider": "mistral-ocr-latest",
  "prompt": "Return Markdown with tables when present."
}
headers = {
  "accept": "application/json",
  "x-api-key": "YOUR_API_KEY",
  "Content-Type": "application/json"
}
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print(resp.status_code)
print(resp.json())`;

const ocrJava = `import java.net.http.*;
import java.net.URI;
import java.time.Duration;

public class OCRClient {
  public static void main(String[] args) throws Exception {
    HttpClient client = HttpClient.newBuilder()
      .connectTimeout(Duration.ofSeconds(20))
      .build();

    String json = """
    {
      "fileName": "sample.png",
      "fileBase64": "<BASE64_WITHOUT_PREFIX>",
      "language": "en",
      "documentType": "INVOICE",
      "provider": "mistral-ocr-latest",
      "prompt": "Return Markdown with tables when present."
    }
    """;

    HttpRequest req = HttpRequest.newBuilder()
      .uri(URI.create("http://localhost:8000/v1/ocr"))
      .header("accept", "application/json")
      .header("x-api-key", "YOUR_API_KEY")
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();

    HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
    System.out.println(res.statusCode());
    System.out.println(res.body());
  }
}`;

/* ----- /v1/correct ----- */

const correctCurl = `curl -X 'POST' \\
  'http://localhost:8000/v1/correct' \\
  -H 'accept: application/json' \\
  -H 'x-api-key: YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{
  "text": "raw OCR text here",
  "model": "models/gemma-3-12b-it",
  "prompt": "Fix formatting; return valid Markdown."
}'`;

const correctJS = `async function correctOCR() {
  const res = await fetch("http://localhost:8000/v1/correct", {
    method: "POST",
    headers: {
      "accept": "application/json",
      "x-api-key": "YOUR_API_KEY",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: "raw OCR text here",
      model: "models/gemma-3-12b-it",
      prompt: "Fix formatting; return valid Markdown."
    })
  });
  console.log(await res.json());
}
correctOCR();`;

const correctPy = `import requests

url = "http://localhost:8000/v1/correct"
payload = {
  "text": "raw OCR text here",
  "model": "models/gemma-3-12b-it",
  "prompt": "Fix formatting; return valid Markdown."
}
headers = {
  "accept": "application/json",
  "x-api-key": "YOUR_API_KEY",
  "Content-Type": "application/json"
}
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print(resp.status_code)
print(resp.json())`;

const correctJava = `import java.net.http.*;
import java.net.URI;

public class CorrectClient {
  public static void main(String[] args) throws Exception {
    HttpClient client = HttpClient.newHttpClient();

    String json = """
    {
      "text": "raw OCR text here",
      "model": "models/gemma-3-12b-it",
      "prompt": "Fix formatting; return valid Markdown."
    }
    """;

    HttpRequest req = HttpRequest.newBuilder()
      .uri(URI.create("http://localhost:8000/v1/correct"))
      .header("accept", "application/json")
      .header("x-api-key", "YOUR_API_KEY")
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();

    HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
    System.out.println(res.statusCode());
    System.out.println(res.body());
  }
}`;

/* ----- /v1/chat ----- */

const chatCurl = `curl -X 'POST' \\
  'http://localhost:8000/v1/chat' \\
  -H 'accept: application/json' \\
  -H 'x-api-key: YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{
  "message": "Summarize key dates",
  "context": "full document text..."
}'`;

const chatJS = `async function documentChat() {
  const res = await fetch("http://localhost:8000/v1/chat", {
    method: "POST",
    headers: {
      "accept": "application/json",
      "x-api-key": "YOUR_API_KEY",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message: "Summarize key dates",
      context: "full document text..."
    })
  });
  console.log(await res.json());
}
documentChat();`;

const chatPy = `import requests

url = "http://localhost:8000/v1/chat"
payload = {
  "message": "Summarize key dates",
  "context": "full document text..."
}
headers = {
  "accept": "application/json",
  "x-api-key": "YOUR_API_KEY",
  "Content-Type": "application/json"
}
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print(resp.status_code)
print(resp.json())`;

const chatJava = `import java.net.http.*;
import java.net.URI;

public class ChatClient {
  public static void main(String[] args) throws Exception {
    HttpClient client = HttpClient.newHttpClient();

    String json = """
    {
      "message": "Summarize key dates",
      "context": "full document text..."
    }
    """;

    HttpRequest req = HttpRequest.newBuilder()
      .uri(URI.create("http://localhost:8000/v1/chat"))
      .header("accept", "application/json")
      .header("x-api-key", "YOUR_API_KEY")
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();

    HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
    System.out.println(res.statusCode());
    System.out.println(res.body());
  }
}`;

/* =========================
   Page
   ========================= */

export default function Docs() {
    const sections: Array<{
        id: string;
        title: string;
        subtitle: string;
        snippets: Record<Lang, string>;
    }> = [
        {
            id: "ocr",
            title: "OCR Endpoint",
            subtitle: "Send a PDF/image (base64) to extract text. Prompt can shape Markdown/tables.",
            snippets: {
                curl: ocrCurl,
                javascript: ocrJS,
                python: ocrPy,
                java: ocrJava,
            },
        },
        {
            id: "correct",
            title: "OCR Correction",
            subtitle: "Normalize and clean OCR output using an LLM.",
            snippets: {
                curl: correctCurl,
                javascript: correctJS,
                python: correctPy,
                java: correctJava,
            },
        },
        {
            id: "chat",
            title: "Document Chat",
            subtitle: "Ask questions over extracted content using your own context.",
            snippets: {
                curl: chatCurl,
                javascript: chatJS,
                python: chatPy,
                java: chatJava,
            },
        },
    ];

    return (
        <div className="mx-auto max-w-6xl px-4 py-10 space-y-10">
            <header className="space-y-2">
                <h1 className="text-3xl font-extrabold tracking-tight">Visionary OCR API — Examples</h1>
                <p className="text-gray-600">
                    Plain, copy-ready requests in curl, JavaScript, Python, and Java. Uses{" "}
                    <span className="font-mono">http://localhost:8000</span> and the headers you provided.
                </p>
                <div className="flex flex-wrap gap-2">
                    <div className="rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm">
                        Base URL: <span className="font-mono">http://localhost:8000</span>
                    </div>
                    <div className="rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm">
                        Auth header: <span className="font-mono">x-api-key</span>
                    </div>
                    <div className="rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm">
                        Content-Type: <span className="font-mono">application/json</span>
                    </div>
                </div>
            </header>

            <main className="space-y-12">
                {sections.map((s) => (
                    <section key={s.id} id={s.id} className="space-y-4">
                        <div className="flex items-baseline justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-bold">{s.title}</h2>
                                <p className="text-gray-600">{s.subtitle}</p>
                            </div>
                        </div>
                        <CodeTabs snippets={s.snippets}/>
                    </section>
                ))}
            </main>
        </div>
    );
}
