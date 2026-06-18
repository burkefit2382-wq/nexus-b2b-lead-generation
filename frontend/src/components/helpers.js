export const CATEGORY_LABELS = { home_remodeling: "Remodeling", cleaning: "Cleaning" };

export const cat = (c) => CATEGORY_LABELS[c] || c || "—";

export const scoreClass = (s) => {
  if (s >= 70) return "hot";
  if (s >= 45) return "warm";
  return "cold";
};

let _uidSeq = 0;
export const nextUid = () => `uid_${Date.now()}_${_uidSeq++}`;
