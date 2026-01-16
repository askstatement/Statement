export function formatDate(input, format) {
  try {
    let date;

    // Normalize input → Date object
    if (input instanceof Date) {
      date = input;
    } else if (typeof input === "number") {
      // Detect seconds vs milliseconds
      date = new Date(
        input < 1e12 ? input * 1000 : input
      );
    } else if (typeof input === "string") {
      date = new Date(input);
    } else {
      throw new Error("Unsupported date input type");
    }

    if (isNaN(date)) {
      throw new Error("Invalid date value");
    }

    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    // Normalize time to midnight for comparison
    const normalize = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());

    if (normalize(date).getTime() === normalize(today).getTime()) {
      return "Today";
    }
    if (normalize(date).getTime() === normalize(yesterday).getTime()) {
      return "Yesterday";
    }

    const pad = (value, length = 2) => String(value).padStart(length, "0");

    const monthsShort = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    const monthsLong = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];

    const tokens = {
      YYYY: date.getFullYear(),
      YY: String(date.getFullYear()).slice(-2),

      MMMM: monthsLong[date.getMonth()],
      MMM: monthsShort[date.getMonth()],

      MM: pad(date.getMonth() + 1),
      M: date.getMonth() + 1,

      DD: pad(date.getDate()),
      D: date.getDate(),

      HH: pad(date.getHours()),
      H: date.getHours(),

      hh: pad(date.getHours() % 12 || 12),
      h: date.getHours() % 12 || 12,

      mm: pad(date.getMinutes()),
      ss: pad(date.getSeconds())
    };

    return format.replace(
      /YYYY|YY|MMMM|MMM|MM|M|DD|D|HH|H|hh|h|mm|ss/g,
      match => tokens[match]
    );
  } catch (error) {
    return input
  }
}

export function shortenMonths(months) {
  const monthMap = {
    January: "Jan", February: "Feb", March: "Mar", April: "Apr",
    May: "May", June: "Jun", July: "Jul", August: "Aug",
    September: "Sep", October: "Oct", November: "Nov", December: "Dec"
  };

  return months.map(monthStr => {
    let result = monthStr;
    for (const [full, short] of Object.entries(monthMap)) {
      const regex = new RegExp(full, "gi"); // case-insensitive global replace
      result = result.replace(regex, short);
    }
    return result;
  });
}