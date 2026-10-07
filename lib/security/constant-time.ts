import { createHash, timingSafeEqual } from "node:crypto";

export function constantTimeMatch(left: string, right: string): boolean {
  if (left.length > 256 || right.length > 256) return false;
  const leftDigest = createHash("sha256").update(left).digest();
  const rightDigest = createHash("sha256").update(right).digest();
  return timingSafeEqual(leftDigest, rightDigest) && left === right;
}
