/**
 * ╔═══════════════════════════════════════════════════════════════╗
 * ║  TDD — Jakku Amruth (Team Lead)                              ║
 * ║  Component: ModelSelector — Radix UI Select dropdown         ║
 * ║  Run:  cd frontend && npx vitest run --reporter=verbose      ║
 * ╚═══════════════════════════════════════════════════════════════╝
 *
 * Tests covering:
 *   - Render, initial data fetch, trigger display
 *   - Dropdown open/close and option listing
 *   - Model selection (different model, same model)
 *   - Disabled state during model switching
 *   - Downloading indicator / loading state
 *   - API error resilience
 *   - Trigger text update after selection
 *
 * Radix UI Select renders options in a portal, so we use
 * findByRole("option") to wait for them after clicking.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModelSelector } from "../ModelSelector";

// ── Mock data ──────────────────────────────────────────────────────

const mockModels = [
  { name: "resnet50", display_name: "ResNet50", size_mb: 96, is_loaded: false, is_active: true, status: "loaded" },
  { name: "efficientnet_b0", display_name: "EfficientNet-B0", size_mb: 18, is_loaded: false, is_active: false, status: "unavailable" },
  { name: "vit_b_16", display_name: "ViT-B/16", size_mb: 344, is_loaded: false, is_active: false, status: "unavailable" },
];

const mockGetModels = vi.fn();
const mockSelectModel = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    getModels: (...args: unknown[]) => mockGetModels(...args),
    selectModel: (...args: unknown[]) => mockSelectModel(...args),
  },
}));

function renderSelector() {
  return render(<ModelSelector />);
}

// ── Tests ──────────────────────────────────────────────────────────

describe("ModelSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetModels.mockResolvedValue({ models: mockModels });
    mockSelectModel.mockResolvedValue({ success: true, active_model: "vit_b_16" });
  });

  // ── Initial Render & Data Fetch ──────────────────────────────────

  it("renders a select trigger with CPU icon", async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });
  });

  it("fetches models from API on mount", async () => {
    renderSelector();
    await waitFor(() => {
      expect(mockGetModels).toHaveBeenCalledTimes(1);
    });
  });

  it("shows the active model name in the trigger", async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toHaveTextContent("ResNet50");
    });
  });

  it("shows a status dot in the trigger for the active model", async () => {
    renderSelector();
    await waitFor(() => {
      expect(screen.getByRole("combobox").innerHTML).toContain("bg-green-500");
    });
  });

  // ── Dropdown & Options ───────────────────────────────────────────

  it("opens dropdown with three model options on click", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));

    const options = await screen.findAllByRole("option");
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent("ResNet50");
    expect(options[1]).toHaveTextContent("EfficientNet-B0");
    expect(options[2]).toHaveTextContent("ViT-B/16");
  });

  it("shows model size in MB for each option", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));
    await user.click(screen.getByRole("combobox"));

    // Size labels render inside options (portal) — wait for them
    await screen.findByText("96MB");
    expect(screen.getByText("96MB")).toBeInTheDocument();
    expect(screen.getByText("18MB")).toBeInTheDocument();
    expect(screen.getByText("344MB")).toBeInTheDocument();
  });

  it("shows green dot for loaded models, gray for unavailable", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));
    await user.click(screen.getByRole("combobox"));

    const options = await screen.findAllByRole("option");
    expect(options).toHaveLength(3);

    // ResNet50 (loaded) → green; others (unavailable) → gray
    expect(options[0].innerHTML).toContain("bg-green-500");
    expect(options[1].innerHTML).toContain("bg-gray-500");
    expect(options[2].innerHTML).toContain("bg-gray-500");
  });

  // ── Model Selection ──────────────────────────────────────────────

  it("calls selectModel when user picks a different model", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));
    const options = await screen.findAllByRole("option");
    await user.click(options[2]); // ViT-B/16

    await waitFor(() => {
      expect(mockSelectModel).toHaveBeenCalledWith("vit_b_16");
    });
  });

  it("does not call selectModel when user picks the already active model", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));
    const options = await screen.findAllByRole("option");
    await user.click(options[0]); // ResNet50 is already active

    // Radix Select ignores same-value selection, so no API call
    expect(mockSelectModel).not.toHaveBeenCalled();
  });

  // ── Loading / Switching States ───────────────────────────────────

  it("disables the select while switching", async () => {
    mockSelectModel.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ success: true }), 500)),
    );
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));
    const options = await screen.findAllByRole("option");
    await user.click(options[2]); // ViT-B/16

    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeDisabled();
    });
  });

  it("shows downloading indicator while model is loading", async () => {
    mockSelectModel.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ success: true }), 500)),
    );
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));
    const options = await screen.findAllByRole("option");
    await user.click(options[2]); // ViT-B/16

    await waitFor(() => {
      expect(screen.getByText("Downloading…")).toBeInTheDocument();
    });
  });

  // ── Error Handling ───────────────────────────────────────────────

  it("handles API error gracefully", async () => {
    mockGetModels.mockRejectedValue(new Error("Network error"));
    renderSelector();
    await waitFor(() => {
      // Should not crash — just show the default select state
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });
  });

  // ── Post-Selection UI Update ─────────────────────────────────────

  it("updates trigger display after model selection", async () => {
    const user = userEvent.setup();
    renderSelector();
    await waitFor(() => screen.getByRole("combobox"));

    await user.click(screen.getByRole("combobox"));
    const options = await screen.findAllByRole("option");
    await user.click(options[2]); // ViT-B/16

    await waitFor(() => {
      expect(screen.getByRole("combobox")).toHaveTextContent("ViT-B/16");
    });
  });
});
