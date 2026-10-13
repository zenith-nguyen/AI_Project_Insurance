/** Stable browser client for the Claim Review API.
 * UI code should use these methods instead of scattering fetch calls.
 */
export class ClaimApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.name = "ClaimApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class ClaimReviewClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, options);
    const type = response.headers.get("content-type") || "";
    const payload = type.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) throw new ClaimApiError(response.status, payload?.detail ?? payload);
    return payload;
  }

  health() { return this.request("/health"); }
  readiness() { return this.request("/readiness"); }
  version() { return this.request("/version"); }

  createClaim(claimId, payload) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/intake`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
  }

  startGuidedCapture(claimId) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/capture-sessions`, {method: "POST"});
  }

  uploadEvidence(claimId, {kind, file, captureSessionId = null, challengeStep = null}) {
    const body = new FormData();
    body.append("kind", kind);
    if (captureSessionId) body.append("capture_session_id", captureSessionId);
    if (challengeStep !== null) body.append("challenge_step", String(challengeStep));
    body.append("file", file);
    return this.request(`/claims/${encodeURIComponent(claimId)}/evidence`, {method: "POST", body});
  }

  analyzeClaim(claimId, overrides = {}) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/analyze`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(overrides),
    });
  }

  getAnalysis(claimId) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/analysis`);
  }

  getAuthenticity(claimId, evidenceId) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/evidence/${encodeURIComponent(evidenceId)}/authenticity`);
  }

  saveReview(claimId, payload) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/review`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
  }

  saveCorrection(claimId, payload) {
    return this.request(`/claims/${encodeURIComponent(claimId)}/corrections`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
  }
}
