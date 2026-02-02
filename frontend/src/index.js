import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./App.css";

// Polyfill para fetch en navegadores antiguos
if (!window.fetch) {
  console.warn("Fetch API no soportada, cargando polyfill...");
  require("whatwg-fetch");
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);