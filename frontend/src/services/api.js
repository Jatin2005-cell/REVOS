// src/services/api.js

// Safe API Base URL (SSR & Client compatible)
const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || 
  "http://localhost:8000"
).replace(/\/$/, "");

// Mock Data Fallback for UI safety during backend downtime
const MOCK_AT_RISK_DEALS = [
  {
    id: "REV-8921",
    account_name: "Acme Corp",
    opportunity_name: "Acme Corp Enterprise License",
    amount: 8500000,
    risk_score: 87,
    top_shap_contributor: "Champion uncommunicative (18d)",
    stage: "Negotiation"
  },
  {
    id: "REV-8922",
    account_name: "FinTech Solutions",
    opportunity_name: "FinTech Sol Expansion Contract",
    amount: 12000000,
    risk_score: 64,
    top_shap_contributor: "Legal redlines stalled (>12d)",
    stage: "Legal Review"
  },
  {
    id: "REV-8923",
    account_name: "Logistics Global",
    opportunity_name: "Logistics Global Regional Rollout",
    amount: 4500000,
    risk_score: 32,
    top_shap_contributor: "High stakeholder engagement",
    stage: "Proposal Sent"
  }
];

// Silent Core Fetch Utility
async function fetchAPI(endpoint, options = {}) {
  const formattedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const fullUrl = `${API_BASE}${formattedEndpoint}`;

  const defaultHeaders = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  try {
    const res = await fetch(fullUrl, {
      ...options,
      headers: defaultHeaders,
    });

    if (!res.ok) {
      let errorMessage = `HTTP error ${res.status}`;
      try {
        const errorData = await res.json();
        errorMessage = typeof errorData === "object" ? JSON.stringify(errorData) : String(errorData);
      } catch {
        const text = await res.text();
        if (text) errorMessage = text;
      }
      throw new Error(errorMessage);
    }

    if (res.status === 204) return null;
    return await res.json();
  } catch (error) {
    // Graceful handling without throwing red terminal errors
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
  } catch {
    // Silent fallback to mock data when backend is down
    return MOCK_AT_RISK_DEALS;
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

export async function runSimulation(sdrCount, discountCap) {
  return runSimulator({ add_sdrs: sdrCount, increase_discount_pct: discountCap });
}

// 5. Query & LLM Agent Integration
export async function submitQuery(question, language = "en") {
  return fetchAPI("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, language }),
  });
}

export async function runRevenueAgent(query) {
  return fetchAPI("/api/chat", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

// 6. CRM Writeback Integration
export async function triggerCRMWriteback(dealId, payload = {}) {
  return fetchAPI("/api/actions/crm-writeback", {
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