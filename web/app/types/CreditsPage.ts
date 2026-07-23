export type CreditUsageChartDataset = {
  label: string
  data: number[]
  backgroundColor: string
  borderRadius: number
  maxBarThickness: number
}

export type CreditUsageChart = {
  labels: string[]
  datasets: CreditUsageChartDataset[]
}
