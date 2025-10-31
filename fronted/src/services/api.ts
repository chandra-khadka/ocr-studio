import {CorrectionProvider, OCRProvider} from "../types/enums";

const API_BASE =
    import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') ||
    (window.location.origin.includes('5173')
        ? 'http://localhost:8000' // dev default
        : window.location.origin);

const API_PREFIX = '/v1';

// ===== Generic HTTP helper =====
async function http<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
        headers: {
            'Content-Type': 'application/json',
            // Optional: if you set API_KEY in backend
            ...(import.meta.env.VITE_API_KEY ? {'x-api-key': import.meta.env.VITE_API_KEY} : {}),
        },
        ...init,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

// ===== Shared helpers =====
function stripDataUri(b64: string) {
    const i = b64.indexOf("base64,");
    return i >= 0 ? b64.slice(i + 7) : b64;
}

// ===== Types: models, health (optional) =====
export type ModelsResponse = {
    ocr: string[];
    correction: string[];
};

export type HealthResponse = { status: "ok" };

// ===== /v1/ocr =====
export type OCRRequest = {
    fileName: string;
    fileBase64: string;                // raw base64 (no data:uri)
    language: string;                  // e.g., "ENGLISH" | "NEPALI" | "AUTO_DETECT"
    documentType: string;              // e.g., "IMAGE" | "CTZN_FRONT" | ...
    provider: string;                  // "PROVIDER:MODEL", e.g. "GEMINI:gemini-2.0-flash-lite-001"
    prompt?: string;
};

export type OCRResponse = {
    text: string;
    pages?: number | null;
    images?: string[] | null;
};

// ===== /v1/correct =====
export type CorrectionRequest = {
    text: string;
    model: string;                     // "PROVIDER:MODEL", e.g. "GEMINI_OPENSOURCE:gemma-3-4b-it"
    prompt?: string;
    document_type?: string;
};

export type CorrectionResponse = {
    corrected: string;
};

// ===== /v1/chat =====
export type ChatRequest = { message: string; context?: string };
export type ChatResponse = { reply: string };

// ===== /v1/ocr_premium =====
// Back-end expects provider + (optional) provider_config.{ocr_model, correction_model}
// and exactly ONE of { image_url, base64_image }.

type OCRPremiumCommon = {
    ocr_provider: string;              // e.g. "MISTRAL" | "GEMINI_OPENSOURCE" | "VLLM" | ...
    correction_provider: string;       // e.g. "NONE" | "GEMINI_OPENSOURCE" | ...
    document_type: string;             // e.g. "IMAGE" | "CTZN_FRONT" | ...
    document_format: string;           // e.g. "STANDARD"
    language: string;                  // e.g. "AUTO_DETECT"
    enable_json_parsing?: boolean;
    use_segmentation?: boolean;
    max_pdf_pages?: number;
    pdf_dpi?: number;
    custom_prompt?: string;
    provider_config?: {
        ocr_model?: string;
        correction_model?: string;
    };
};

type OCRPremiumWithUrl = OCRPremiumCommon & {
    image_url: string;
    base64_image?: never;
};

type OCRPremiumWithBase64 = OCRPremiumCommon & {
    base64_image: string;              // raw base64 (no data:uri)
    image_url?: never;
};

export type OCRPremiumRequest = OCRPremiumWithUrl | OCRPremiumWithBase64;

export type OCRPremiumResponse = {
    // UI-compatible primary fields:
    text: string;
    pages?: number | null;
    images?: string[] | null;

    // Optional extras:
    raw_text?: string | null;
    corrected_text?: string | null;
    structured_data?: Record<string, any> | null;
    meta?: Record<string, any> | null;
};

// ===== API calls =====
export async function health(): Promise<HealthResponse> {
    return http("/health");
}


type ProviderModelsResp = { ocr?: string[]; correction?: string[] };

export async function listOCRModels(provider: OCRProvider): Promise<string[]> {
    const q = encodeURIComponent(provider);
    const res = await http<ProviderModelsResp>(`/models?ocr_provider=${q}`);
    return res.ocr ?? [];
}

// Just Correction list for selected provider
export async function listCorrectionModels(provider: CorrectionProvider): Promise<string[]> {
    const q = encodeURIComponent(String(provider));
    const res = await http<ProviderModelsResp>(`/models?correction_provider=${q}`);
    return res.correction ?? [];
}

// (Optional) Full map for UI debugging/inspection
export type FullModelsMap = {
    ocr: Record<string, string[]>;
    correction: Record<string, string[]>;
};

export async function listAllModelsMap(): Promise<FullModelsMap> {
    return http<FullModelsMap>(`/models`);
}

export async function runOCR(req: OCRRequest): Promise<OCRResponse> {
    const payload = {...req, fileBase64: stripDataUri(req.fileBase64)};
    return http("/ocr", {method: "POST", body: JSON.stringify(payload)});
}

export async function runCorrection(req: CorrectionRequest): Promise<CorrectionResponse> {
    return http("/correct", {method: "POST", body: JSON.stringify(req)});
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
    return http("/chat", {method: "POST", body: JSON.stringify(req)});
}

export async function runOCRPremium(req: OCRPremiumRequest): Promise<OCRPremiumResponse> {
    const payload: any = {...req};
    if ("base64_image" in payload && payload.base64_image) {
        payload.base64_image = stripDataUri(payload.base64_image);
    }
    return http("/ocr_premium", {method: "POST", body: JSON.stringify(payload)});
}


export type OrgInquiry = {
    orgName: string
    contactName: string
    email: string
    phone?: string
    teamSize: string
    monthlyDocs: string
    useCases: string[]
    message?: string
    source?: string
}

export async function sendOrgInquiry(payload: OrgInquiry): Promise<{ ok: boolean }> {
    try {
        const res = await fetch(`${API_BASE}${API_PREFIX}/contact/org`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(import.meta.env.VITE_API_KEY ? {"x-api-key": import.meta.env.VITE_API_KEY} : {}),
            },
            body: JSON.stringify(payload),
        });

        if (!res.ok) return {ok: false};

        // Try to parse JSON if server returns it; otherwise just succeed.
        try {
            const data = await res.json();
            if (data && typeof data === "object" && "ok" in data) {
                return {ok: Boolean((data as any).ok)};
            }
        } catch {
            // No JSON (e.g., 204) — that's fine.
        }
        return {ok: true};
    } catch {
        return {ok: false};
    }
}
