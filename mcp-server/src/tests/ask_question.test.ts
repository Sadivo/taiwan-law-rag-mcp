import { describe, it, expect, vi } from "vitest";
import * as fc from "fast-check";
import { handleAskLawQuestion } from "../tools/ask_question.js";
import type { RAGClient, ChatResponse, Citation } from "../clients/rag_client.js";

describe("Property 13: MCP Tool 格式化輸出包含引用條文", () => {
  it("Feature: rag-generation, Property 13: 格式化輸出包含引用條文 - Validates: Requirements 9.2, 9.3", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(
          fc.record({
            law_name: fc.string(),
            article_no: fc.string(),
          })
        ),
        fc.string({ minLength: 1 }),
        async (citations: Citation[], answer: string) => {
          const mockResponse: ChatResponse = {
            answer,
            citations,
            query_time: 0.1,
          };

          const mockClient = {
            chat: vi.fn().mockResolvedValue(mockResponse),
          } as unknown as RAGClient;

          const result = await handleAskLawQuestion(
            { question: "test question", top_k: 5 },
            mockClient
          );

          const text = result.content[0]!.text;

          // Answer should be in the output
          expect(text).toContain(answer);

          // Each citation should appear in the output
          for (const citation of citations) {
            expect(text).toContain(`- ${citation.law_name} ${citation.article_no}`);
          }

          // If there are citations, the header should be present
          if (citations.length > 0) {
            expect(text).toContain("**引用條文：**");
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
