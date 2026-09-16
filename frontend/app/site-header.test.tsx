import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteHeader } from "./site-header";

describe("SiteHeader", () => {
  it("shows the product name as a link back to the list", () => {
    render(<SiteHeader />);

    const link = screen.getByRole("link", { name: "Customer Pulse" });
    expect(link).toHaveAttribute("href", "/");
  });
});
