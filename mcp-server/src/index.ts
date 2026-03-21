import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { RAGClient } from "./clients/rag_client.js";
import { semanticSearchTool, handleSemanticSearch } from "./tools/search.js";
import { exactSearchTool, handleExactSearch } from "./tools/exact_search.js";
import { lawSearchTool, handleLawSearch } from "./tools/law_search.js";
import { getLawTool, handleGetLaw } from "./tools/get_law.js";
import { compareTool, handleCompare } from "./tools/compare.js";

// Initialize the API client connecting to the FastAPI RAG backend
const client = new RAGClient();

const server = new Server(
  {
    name: "taiwan-law-rag",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      semanticSearchTool,
      exactSearchTool,
      lawSearchTool,
      getLawTool,
      compareTool,
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;

    if (!args) {
      throw new Error("No arguments provided");
    }

    switch (name) {
      case "semantic_search":
        return await handleSemanticSearch(args, client);
      case "exact_search":
        return await handleExactSearch(args, client);
      case "search_law_by_name":
        return await handleLawSearch(args, client);
      case "get_law_full_text":
        return await handleGetLaw(args, client);
      case "compare_laws":
        return await handleCompare(args, client);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error: any) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Taiwan Law RAG MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Server abort:", error);
  process.exit(1);
});
