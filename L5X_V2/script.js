// This script is responsible for rendering the Mermaid diagram using the ELK layout engine.

async function loadELKRender() {
  try {
    // Explicitly register the loader
    await mermaid.registerLayoutLoaders([elkLayouts]);

    // Initialize without auto-starting
    mermaid.initialize({
      startOnLoad: false,
      layout: "elk",
      look: "handCoded",
      securityLevel: "loose",
      flowchart: { defaultRenderer: "elk" }, // Double-force the renderer
    });

    // Manually run the renderer now that we are 100% sure ELK is registered
    await mermaid.run();
    console.log("ELK Layout loaded successfully.");
    document.getElementById("loading-overlay").style.display = "none";
    return true; // Indicate successful load of ELK
  } catch (err) {
    console.error("ELK Layout failed to load:", err);
    return false; // Indicate failure to load ELK
  }
}

async function loadStandardRender() {
  // Initialize without auto-starting
  mermaid.initialize({
    startOnLoad: true,
    layout: "dagre",
    securityLevel: "loose",
  });

  try {
    await mermaid.run();
    console.error("Standard Layout loaded successfully.");
    document.getElementById("loading-overlay").style.display = "none";
    return true; // Indicate successful load of standard layout
  } catch (err2) {
    console.error("Standard Layout failed to load:", err2);
    return false; // Indicate failure to load standard layout
  }
}

async function renderDiagram() {
  try {
    const elkSuccess = await loadELKRender();
    if (!elkSuccess) {
      console.warn("ELK render failed, attempting dagre render as fallback...");
      const stdSuccess = await loadStandardRender();
      if (!stdSuccess) {
        console.error(
          "Both standard and ELK renders failed. Diagram cannot be displayed.",
        );
        document.getElementById("loading-overlay").style.display = "none";
      }
    } else {
      document.getElementById("loading-overlay").style.display = "none";
    }
  } catch (stdErr) {
    console.error("Error during standard render:", stdErr);
    document.getElementById("loading-overlay").style.display = "none";
    // Add error info to the page for user visibility
    const errorDiv = document.createElement("div");
    errorDiv.style.position = "absolute";
    errorDiv.style.top = "50%";
    errorDiv.style.left = "50%";
    errorDiv.style.transform = "translate(-50%, -50%)";
    errorDiv.style.color = "red";
    errorDiv.style.fontSize = "14px";
    errorDiv.textContent =
      "Failed to render diagram. Please check the console for errors.";
    document.body.appendChild(errorDiv);
  }
}

async function main() {
  // Wait until the CDN files are actually parsed
  while (typeof mermaid === "undefined" || typeof elkLayouts === "undefined") {
    await new Promise((r) => setTimeout(r, 50));
  }
  // Use a timer instead
  // await new Promise((r) => setTimeout(r, 500));

  try {
    console.log("Starting diagram rendering...");
    renderDiagram();
  } catch (finalErr) {
    console.error("Unexpected error during rendering:", finalErr);
    document.getElementById("loading-overlay").style.display = "none";
  }
}

// Start the rendering process
main();
