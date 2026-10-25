export function parseAuctionDateMs(value) {
  if (!value) return 0;

  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function canCloseAuction(auction, isAdmin = false) {
  if (!auction || auction.status !== 'ACTIVE') return false;

  if (isAdmin) return true;

  const deadline = parseAuctionDateMs(auction.end_time);
  const expired =
    auction.is_expired === true ||
    Number(auction.seconds_remaining) <= 0 ||
    (deadline > 0 && deadline <= Date.now());

  return expired;
}

export function canCancelAuction(auction, isAdmin = false) {
  if (!auction || auction.status !== 'ACTIVE') return false;

  if (isAdmin) return true;

  const totalBids = Number(auction.total_bids ?? 0);
  return totalBids === 0;
}
