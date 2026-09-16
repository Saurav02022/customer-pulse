import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("asks the owner to select a relationship and selects nothing itself", () => {
    render(<Home />);

    expect(
      screen.getByText("Select a relationship to see its details."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
