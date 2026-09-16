import Link from "next/link";

// The product name is the only navigation: it leads back to the list.
export function SiteHeader() {
  return (
    <header className="border-b border-neutral-200">
      <div className="mx-auto max-w-6xl px-4 py-1">
        <Link
          href="/"
          className="inline-block py-2 font-semibold text-neutral-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
        >
          Customer Pulse
        </Link>
      </div>
    </header>
  );
}
