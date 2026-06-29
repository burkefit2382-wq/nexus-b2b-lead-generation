import React, { useEffect } from "react";

// The public marketing/launch site ("LeadGen Virtual Hub") is served verbatim from
// /public/launch/ and framed full-viewport so its self-contained CSS/JS stay isolated
// from the NEXUS app styles. CTAs inside (Console Login / Open console) break out to
// the real React app at /dashboard via target="_top".
export default function Landing() {
  useEffect(() => {
    const prev = document.title;
    document.title = "LeadGen Virtual Hub";
    return () => { document.title = prev; };
  }, []);

  return (
    <iframe
      title="LeadGen Virtual Hub"
      src="/launch/index.html"
      data-testid="launch-landing-frame"
      style={{ position: "fixed", inset: 0, width: "100%", height: "100%", border: "none", display: "block" }}
    />
  );
}
