import "dotenv/config";
import express from "express";
import { Agent } from "@cursor/sdk";

const app = express();
const PORT = 3001;

if (!process.env.CURSOR_API_KEY) {
  throw new Error(
    "Missing CURSOR_API_KEY. Add it to agent-backend/.env or export it in your shell."
  );
}

app.use(express.json());

type ResolutionStatus = "staged_for_approval" | "escalated";

type BreakResolution = {
  status: ResolutionStatus;
  policy_cited: string;
  audit_rationale: string;
  drafted_email?: string;
};

function parseResolutionJson(rawResponse: string): BreakResolution {
  const trimmed = rawResponse.trim();
  const withoutCodeFence = trimmed
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");

  const parsed = JSON.parse(withoutCodeFence) as Partial<BreakResolution>;

  if (
    parsed.status !== "staged_for_approval" &&
    parsed.status !== "escalated"
  ) {
    throw new Error("Invalid status in agent response");
  }

  if (typeof parsed.policy_cited !== "string" || parsed.policy_cited.trim() === "") {
    throw new Error("Invalid policy_cited in agent response");
  }

  if (
    typeof parsed.audit_rationale !== "string" ||
    parsed.audit_rationale.trim() === ""
  ) {
    throw new Error("Invalid audit_rationale in agent response");
  }

  if (parsed.status === "escalated") {
    if (typeof parsed.drafted_email !== "string" || parsed.drafted_email.trim() === "") {
      throw new Error("drafted_email is required when status is escalated");
    }
  } else if (
    parsed.drafted_email !== undefined &&
    parsed.drafted_email !== null &&
    String(parsed.drafted_email).trim() !== ""
  ) {
    throw new Error("drafted_email must be empty/omitted when staged_for_approval");
  }

  return {
    status: parsed.status,
    policy_cited: parsed.policy_cited.trim(),
    audit_rationale: parsed.audit_rationale.trim(),
    drafted_email:
      parsed.status === "escalated" ? String(parsed.drafted_email).trim() : undefined,
  };
}

app.post("/resolve-break", async (req, res) => {
  const { breakDetails } = req.body ?? {};

  if (!breakDetails) {
    res.status(400).json({ error: "Missing required field: breakDetails" });
    return;
  }

  const prompt = `You are a Hedge Fund Middle Office expert.

FUND POLICIES:
- Rule PB-01: Commission discrepancies under $50 are auto-approved.
- Rule TR-02: Price differences under 1 BPS (Basis Point) on US Treasuries are auto-approved.
- Rule EX-01: Any missing trade or wrong Side (Buy/Sell) must be escalated immediately.

Analyze this trade break:
${JSON.stringify(breakDetails)}

Return ONLY a strict JSON object with exactly these keys:
- status: must be exactly "staged_for_approval" or "escalated"
- policy_cited: include the exact rule applied (e.g., "Rule PB-01")
- audit_rationale: professional explanation of the math/reasoning
- drafted_email: include only when status is "escalated" (omit otherwise)

Do not include markdown, code fences, or any extra keys.`;

  try {
    const agent = await Agent.create({
      model: { id: "composer-2" },
      name: "Trade Break Resolver",
      apiKey: process.env.CURSOR_API_KEY,
    });

    let resolution = "";
    const run = await agent.send(prompt, { model: { id: "composer-2" } });

    for await (const message of run.stream()) {
      if (message.type === "assistant") {
        const textChunk = message.message.content
          .filter((block) => block.type === "text")
          .map((block) => block.text)
          .join("");

        if (textChunk) {
          resolution += textChunk;
          // Keep streaming visible in server logs while we aggregate final response.
          process.stdout.write(textChunk);
        }
      }
    }

    await run.wait();
    agent.close();

    const parsedResolution = parseResolutionJson(resolution);
    res.json(parsedResolution);
  } catch (error) {
    console.error("Failed to resolve break with Cursor Agent:", error);
    if (
      error &&
      typeof error === "object" &&
      "cause" in error &&
      (error as { cause?: { code?: string } }).cause?.code === "unauthenticated"
    ) {
      res.status(401).json({
        error:
          "Cursor API authentication failed. Verify CURSOR_API_KEY in agent-backend/.env is valid for your Cursor account.",
      });
      return;
    }
    if (error instanceof SyntaxError || error instanceof Error) {
      res.status(502).json({
        error:
          "Agent returned an invalid response format. Expected strict JSON with status, policy_cited, audit_rationale, and drafted_email (for escalations).",
      });
      return;
    }
    res.status(500).json({ error: "Failed to generate break resolution" });
  }
});

app.listen(PORT, () => {
  console.log(`Agent backend listening on http://localhost:${PORT}`);
});
