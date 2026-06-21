import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RootApp } from "./app/RootApp";
import "./styles.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("SOUL Lab root element was not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <RootApp />
  </StrictMode>,
);
