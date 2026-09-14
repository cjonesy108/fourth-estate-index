import Link from "next/link";
import { ownershipChipForDirectory } from "@/lib/ownership";

export function OwnershipChip({
  directoryOutletSlug,
}: {
  directoryOutletSlug: string;
}) {
  const chip = ownershipChipForDirectory(directoryOutletSlug);
  if (!chip) return null;

  return (
    <p className="text-sm text-gray-600 leading-relaxed">
      <span className="text-xs uppercase tracking-wide text-gray-400 mr-2">Ownership</span>
      <Link href={chip.href} className="hover:underline">
        {chip.line}
      </Link>
      {chip.pending && (
        <>
          <span className="text-gray-300 mx-2">·</span>
          <Link href={chip.href} className="text-xs text-gray-500 hover:underline">
            {chip.pending.headline}
          </Link>
        </>
      )}
    </p>
  );
}
