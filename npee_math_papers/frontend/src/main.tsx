import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "katex/dist/katex.min.css";
import "./styles/tokens.css";
import "./styles/app.css";
import "./styles/features.css";
import "./styles/responsive.css";
import { AppShell } from "./app/AppShell";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppShell />
  </StrictMode>,
);
