export const toIsoDate = (date) => {
  const d = new Date(date);
  return d.toISOString().split("T")[0];
};

export const formatCountdown = (ms) => {
  const total = Math.max(Math.floor(ms / 1000), 0);
  const hours = Math.floor(total / 3600);
  const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${minutes}:${seconds}`;
  }
  return `${minutes}:${seconds}`;
};

export const msUntil = (isoDateTime) => {
  if (!isoDateTime) return 0;
  // Normalize to UTC: Python's datetime.utcnow() serializes without 'Z',
  // so we append it to ensure correct UTC parsing in JS.
  const str = String(isoDateTime);
  const normalized = /[Zz]$/.test(str) || /[+-]\d{2}:?\d{2}$/.test(str) ? str : str + "Z";
  return new Date(normalized).getTime() - Date.now();
};

export const addMinutesIso = (minutes) => {
  const now = new Date();
  now.setMinutes(now.getMinutes() + Number(minutes));
  return now.toISOString();
};

export const toTotalMinutes = (hours, minutes) => {
  const h = Math.max(Number(hours) || 0, 0);
  const m = Math.max(Number(minutes) || 0, 0);
  return (h * 60) + m;
};

export const minutesToHoursMinutes = (totalMinutes) => {
  const total = Math.max(Math.floor(Number(totalMinutes) || 0), 0);
  return {
    hours: Math.floor(total / 60),
    minutes: total % 60,
  };
};

const formatMinutesCompact = (minutes) => {
  const totalMinutes = Math.max(Math.round(Number(minutes) || 0), 0);
  if (totalMinutes <= 0) return "-";

  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const mins = totalMinutes % 60;

  if (days > 0 && hours === 0 && mins === 0) {
    return `${days}d`;
  }

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (mins > 0 || parts.length === 0) parts.push(`${mins}m`);
  return parts.join(" ");
};

export const formatProjectDuration = (project) => {
  if (!project) return "-";

  if (project.duration_minutes != null) {
    return formatMinutesCompact(project.duration_minutes);
  }

  const value = Number(project.duration_value);
  const unit = String(project.duration_unit || "").toLowerCase();

  if (!Number.isFinite(value) || value <= 0 || !unit) {
    return "-";
  }

  if (unit === "minutes") {
    return formatMinutesCompact(value);
  }
  if (unit === "hours") {
    return formatMinutesCompact(value * 60);
  }
  if (unit === "days") {
    return formatMinutesCompact(value * 24 * 60);
  }

  return "-";
};
