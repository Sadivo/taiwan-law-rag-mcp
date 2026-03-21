import fetch from "node-fetch";

export class RAGClient {
  private baseUrl: string;

  constructor(baseUrl: string = process.env.RAG_API_URL || "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, body: any, retries: number = 3): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        return (await response.json()) as T;
      } catch (error) {
        if (attempt === retries) {
          throw new Error(`Failed to fetch from ${url} after ${retries} attempts: ${error}`);
        }
        await new Promise((res) => setTimeout(res, 1000 * attempt));
      }
    }
    throw new Error("Unreachable");
  }

  async semanticSearch(query: string, top_k: number = 10, filter_category?: string) {
    return this.request<any>("/search/semantic", { query, top_k, filter_category });
  }

  async exactSearch(query: string) {
    return this.request<any>("/search/exact", { query });
  }

  async searchLaw(law_name: string, include_abolished: boolean = false) {
    return this.request<any>("/search/law", { law_name, include_abolished });
  }

  async getLawFullText(law_name: string) {
    return this.request<any>("/law/full", { law_name });
  }

  async compareLaws(law_names: string[], topic: string) {
    return this.request<any>("/law/compare", { law_names, topic });
  }
}
