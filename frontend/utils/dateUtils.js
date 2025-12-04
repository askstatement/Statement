export function formatDateToFriendly(dateInput) {
  const date = new Date(dateInput);
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

  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  return `${months[date.getMonth()]} ${date.getDate()}`;
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