import { describe, expect, it, vi } from "vitest";
import {
  askQuestion,
  characterCount,
  loadClientConfig,
  parseAnswer,
  parseClientConfig,
} from "./ask";
import { clientConfig, refusalAnswer, supportedAnswer } from "../test/fixtures";

describe("answer response validation", (): void => {
  it("does not use inherited properties as server error messages", async (): Promise<void> => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "__proto__", message: "private text" },
          }),
          { status: 500 },
        ),
      ),
    );
    await expect(
      askQuestion("question", new AbortController().signal),
    ).rejects.toThrow("We could not complete the request");
  });
  it("accepts complete supported and refused responses", (): void => {
    expect(parseAnswer(supportedAnswer)).toEqual(supportedAnswer);
    expect(parseAnswer(refusalAnswer)).toEqual(refusalAnswer);
  });

  it.each([
    {},
    { ...supportedAnswer, citations: [] },
    { ...supportedAnswer, supported: "true" },
    { ...supportedAnswer, mode: "no_model" },
    { ...supportedAnswer, reason: "invented" },
    { ...supportedAnswer, verification: { proposed: 0, valid: 1 } },
    { ...supportedAnswer, verification: { proposed: 2, valid: 1 } },
    {
      ...supportedAnswer,
      citations: [{ ...supportedAnswer.citations[0], page: 0 }],
    },
    {
      ...supportedAnswer,
      citations: [{ ...supportedAnswer.citations[0], quote: "" }],
    },
    { ...refusalAnswer, citations: supportedAnswer.citations },
  ])(
    "rejects an inconsistent or malformed response",
    (value: unknown): void => {
      expect((): void => {
        parseAnswer(value);
      }).toThrow();
    },
  );

  it("rejects non-JSON bodies and does not expose unknown error text", async (): Promise<void> => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response("<html>proxy error</html>"))
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              error: {
                code: "unknown_error",
                message: "private server detail",
              },
            }),
            { status: 500 },
          ),
        ),
    );
    const signal = new AbortController().signal;
    await expect(askQuestion("question", signal)).rejects.toThrow(
      "unreadable response",
    );
    await expect(askQuestion("question", signal)).rejects.toThrow(
      "We could not complete",
    );
  });
});

describe("backend-owned workspace settings", (): void => {
  it("accepts nondefault bounds and copies only public fields", (): void => {
    const config = {
      ...clientConfig,
      max_query_characters: 17,
      search_k: 2,
      search_max_k: 7,
      search_strategy: "keyword",
    };
    expect(
      parseClientConfig({ ...config, private_value: "never consumed" }),
    ).toEqual(config);
    expect(characterCount(" A😀B ")).toBe(5);
  });

  it.each([
    null,
    [],
    {},
    { ...clientConfig, max_query_characters: 0 },
    { ...clientConfig, max_query_characters: 20001 },
    { ...clientConfig, max_query_characters: "17" },
    { ...clientConfig, search_k: 2.5 },
    { ...clientConfig, search_k: 51 },
    { ...clientConfig, search_max_k: 101 },
    { ...clientConfig, search_strategy: "other" },
    { ...clientConfig, search_strategy: ["hybrid"] },
  ])(
    "rejects an invalid configuration without guessing defaults",
    (value: unknown): void => {
      expect(() => parseClientConfig(value)).toThrow("could not be verified");
    },
  );

  it("loads the settings and rejects error/non-JSON responses safely", async (): Promise<void> => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(clientConfig)))
      .mockResolvedValueOnce(new Response("private details", { status: 503 }))
      .mockResolvedValueOnce(new Response("<html>proxy failure</html>"));
    vi.stubGlobal("fetch", fetcher);
    const signal = new AbortController().signal;
    await expect(loadClientConfig(signal)).resolves.toEqual(clientConfig);
    expect(fetcher).toHaveBeenNthCalledWith(1, "/api/config", { signal });
    await expect(loadClientConfig(signal)).rejects.toThrow(
      "temporarily unavailable",
    );
    await expect(loadClientConfig(signal)).rejects.toThrow("could not be read");
  });
});
