export const parseAuctionDateMs = (value) => {
  if (!value) return NaN;
  if (value instanceof Date) return value.getTime();
  if (typeof value !== 'string') return new Date(value).getTime();

  const hasTimezone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`).getTime();
};

export const isAuctionExpiredForActions = (auction) => {
  if (!auction) return false;
  if (typeof auction.is_expired === 'boolean') {
    return auction.is_expired || Number(auction.seconds_remaining) <= 0;
  }
  if (auction.seconds_remaining !== undefined && auction.seconds_remaining !== null) {
    return Number(auction.seconds_remaining) <= 0;
  }

  const endTime = parseAuctionDateMs(auction.end_time);
  return Number.isFinite(endTime) && Date.now() >= endTime;
};

export const canCloseAuction = (auction, isAdmin = false) => {
  if (!auction || auction.status !== 'ACTIVE') return false;
  return isAdmin || isAuctionExpiredForActions(auction);
};

export const canCancelAuction = (auction, isAdmin = false) => {
  if (!auction || !['ACTIVE', 'SCHEDULED'].includes(auction.status)) return false;
  return isAdmin || Number(auction.total_bids || 0) === 0;
};
