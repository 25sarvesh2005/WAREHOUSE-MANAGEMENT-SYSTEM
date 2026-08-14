export const STATUS_BADGE_COLORS: Record<string, string> = {
  // Inventory States
  AVAILABLE: "green",
  RESERVED: "amber",
  IN_TRANSIT: "blue",
  RETURN_INSPECTION: "orange",
  DAMAGED: "red",
  QUARANTINED: "purple",
  SHIPPED: "gray",
  RESTOCKED: "green",
  SCRAPPED: "gray",

  // Inbound Receipt Lifecycle
  DRAFT: "gray",
  COMPLETED: "green",
  CANCELLED: "gray",
  DUPLICATE_OVERRIDE: "orange",
  PENDING_OVERRIDE: "orange",

  // Orders & Fulfillment
  PENDING: "amber",
  PARTIALLY_RESERVED: "orange",
  PICKING: "blue",
  PACKED: "purple",
  CLOSED: "gray",
  ASSIGNED: "blue",
  IN_PROGRESS: "amber",
  SHORT_PICK_EXCEPTION: "red",
  LABEL_CREATED: "blue",
  DELIVERED: "green",

  // Transfers
  PENDING_APPROVAL: "amber",
  APPROVED: "blue",
  DISPATCHED: "purple",
  RECEIVED: "green",
  DISCREPANCY_REVIEW: "red",

  // Returns
  EXPECTED: "blue",
  INSPECTION: "orange",
  PARTIALLY_DISPOSED: "amber",
  REJECTED: "gray",

  // Migration & Batches
  STAGED: "gray",
  VALIDATING: "blue",
  VALIDATED: "green",
  VALIDATION_FAILED: "red",
  APPLIED: "green",

  // Master Data & User Status
  ACTIVE: "green",
  INACTIVE: "gray",
  SUSPENDED: "red",
  PENDING_APPROVAL_SELLER: "amber",

  // Priorities
  HIGH: "red",
  MEDIUM: "amber",
  LOW: "gray",
  URGENT: "red",
};

export const STATUS_BADGE_CLASSES: Record<string, string> = {
  green: "bg-emerald-50 text-emerald-700 border border-emerald-200/80 font-medium",
  amber: "bg-amber-50 text-amber-700 border border-amber-200/80 font-medium",
  blue: "bg-blue-50 text-blue-700 border border-blue-200/80 font-medium",
  orange: "bg-orange-50 text-orange-700 border border-orange-200/80 font-medium",
  red: "bg-rose-50 text-rose-700 border border-rose-200/80 font-medium",
  purple: "bg-purple-50 text-purple-700 border border-purple-200/80 font-medium",
  gray: "bg-slate-100 text-slate-700 border border-slate-200 font-medium",
};

export const SELLABLE_STATES = ["AVAILABLE"];
