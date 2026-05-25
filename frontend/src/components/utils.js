export const SIGNAL_META = {
  high_utilization: {
    label: 'High Utilization',
    short: 'High Util.',
    description: 'Credit utilization above 80%',
    color: '#F59E0B',
    bg: '#FEF3C7',
  },
  inactivity: {
    label: 'Inactivity',
    short: 'Inactivity',
    description: 'No transactions in 30+ days',
    color: '#D97706',
    bg: '#FDE68A',
  },
  unresolved_complaints: {
    label: 'Unresolved Complaints',
    short: 'Complaints',
    description: 'Open complaints with no resolution',
    color: '#B45309',
    bg: '#FCD34D',
  },
  competitor_interest: {
    label: 'Competitor Interest',
    short: 'Competitor',
    description: 'Clicked competitor offers',
    color: '#92400E',
    bg: '#FEF08A',
  },
  spend_drop: {
    label: 'Spend Drop',
    short: 'Spend Drop',
    description: 'Monthly spending declined over 40%',
    color: '#78350F',
    bg: '#FEF9C3',
  },
}

export function formatTimestamp(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}