export const toLocalDateTimeInput = (date) => {
  const rounded = new Date(Math.ceil(date.getTime() / 60000) * 60000);
  const local = new Date(rounded.getTime() - rounded.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
};

export const toUtcISOString = (localDateTime) => {
  const date = new Date(localDateTime);
  if (!localDateTime || !Number.isFinite(date.getTime())) {
    throw new RangeError('Enter a valid auction date and time.');
  }
  return date.toISOString();
};

export const addLocalDaysToDateTime = (localDateTime, days) => {
  const date = new Date(localDateTime);
  date.setDate(date.getDate() + days);
  return toLocalDateTimeInput(date);
};

export const getMinimumAuctionEnd = (startDateTime, now = new Date()) => {
  const minimumNow = new Date(Math.ceil(now.getTime() / 60000) * 60000);
  const start = new Date(startDateTime);
  const minimumAfterStart = Number.isFinite(start.getTime())
    ? new Date(start.getTime() + 60000)
    : minimumNow;
  return toLocalDateTimeInput(minimumAfterStart > minimumNow ? minimumAfterStart : minimumNow);
};

export const validateAuctionSchedule = (startDateTime, endDateTime, now = new Date()) => {
  const start = new Date(startDateTime);
  const end = new Date(endDateTime);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) {
    return 'Enter valid start and end date/time values.';
  }
  if (start < now) {
    return 'Auction start date and time cannot be in the past.';
  }
  if (end <= start) {
    return 'Auction end date and time must be later than the start date and time.';
  }
  if (end < now) {
    return 'Auction end date and time cannot be in the past.';
  }
  return null;
};
