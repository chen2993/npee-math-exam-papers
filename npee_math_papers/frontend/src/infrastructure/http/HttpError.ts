/**
 * Shared HTTP error type.
 *
 * Carries the status and the parsed server detail so callers can branch on
 * "not found" vs "conflict" vs "invalid" (the API maps them to 404/409/400),
 * instead of parsing an error message string.
 */

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: string = "",
  ) {
    super(message);
    this.name = "HttpError";
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

/** Read a failed response into an {@link HttpError} with a readable message. */
export async function readError(response: Response, prefix: string): Promise<HttpError> {
  let detail = "";
  try {
    detail = (await response.text()).trim();
  } catch {
    detail = "";
  }
  // FastAPI puts the message in {"detail": "..."}; unwrap it when present.
  let message = detail;
  try {
    const parsed = JSON.parse(detail);
    if (parsed && typeof parsed === "object" && typeof parsed.detail === "string") {
      message = parsed.detail;
    }
  } catch {
    /* plain text body */
  }
  return new HttpError(`${prefix} ${response.status}${message ? `：${message}` : ""}`, response.status, message);
}
