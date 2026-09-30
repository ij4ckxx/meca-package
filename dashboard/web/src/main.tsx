import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import App from "./App";
import { BatchProvider } from "./context/BatchContext";
import { ThemeProvider } from "./context/ThemeContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <BatchProvider>
          <App />
          <Toaster richColors position="top-right" />
        </BatchProvider>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
);
