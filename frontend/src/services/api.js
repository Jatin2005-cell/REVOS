const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Core Reusable Fetch Wrapper
async function fetchAPI(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 
        "Content-Type": "application/json", 
        ...options.headers 
      },
      ...options,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API error ${res.status}: ${err}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`API Fetch Error on ${endpoint}:`, error);
    throw error;
  }
}

// 1. Dashboard & Deals APIs
export async function getDashboardSummary() {
  return fetchAPI("/api/dashboard/summary");
}

export async function getDeals({ stage, minRisk, sortBy, limit } = {}) {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (minRisk) params.set("min_risk", minRisk);
  if (sortBy) params.set("sort_by", sortBy);
  if (limit) params.set("limit", limit);
  
  const queryString = params.toString();
  return fetchAPI(`/api/deals${queryString ? `?${queryString}` : ""}`);
}

export async function getDealDetail(dealId) {
  return fetchAPI(`/api/deals/${dealId}`);
}

export async function getTopRiskDeals(limit = 10) {
  return fetchAPI(`/api/risk/top?limit=${limit}`);
}

export async function getAtRiskDeals() {
  try {
    return await fetchAPI("/api/deals/at-risk");
  } catch (error) {
    console.warn("Fallback to top risk deals endpoint:", error);
    return await getTopRiskDeals();
  }
}

// 2. Forecasting & ML Engine APIs
export async function getForecast() {
  return fetchAPI("/api/forecast");
}

export async function trainModels() {
  return fetchAPI("/api/ml/train", { method: "POST" });
}

// 3. Next Best Action (NBA) & Email Drafting
export async function getNBA(dealId) {
  return fetchAPI(`/api/nba/${dealId}`);
}

export async function draftEmail(dealId, tone = "professional") {
  return fetchAPI(`/api/email/draft?deal_id=${dealId}&tone=${tone}`, {
    method: "POST",
  });
}

// 4. What-If Simulator
export async function runSimulator(params) {
  return fetchAPI("/api/simulator", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// Backward compatibility alias for simulator
export async function runSimulation(sdrCount, discountCap) {
  return runSimulator({ add_sdrs: sdrCount, increase_discount_pct: discountCap });
}

// 5. Query & LLM Agent Integration (RAG + ChromaDB)
export async function submitQuery(question, language = "en") {
  return fetchAPI("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, language }),
  });
}

export async function runRevenueAgent(query) {
  return await fetchAPI("/api/chat", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

// 6. CRM Writeback Integration
export async function triggerCRMWriteback(dealId, payload = {}) {
  return await fetchAPI("/api/actions/crm-writeback", {
    method: "POST",
    body: JSON.stringify({ deal_id: dealId, ...payload }),
  });
}

// Utility Helpers
export function formatCurrency(amount) {
  if (!amount && amount !== 0) return "₹0";
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function riskColor(label) {
  if (label === "high_risk" || label === "high") return "high";
  if (label === "medium_risk" || label === "medium") return "medium";
  return "low";
}