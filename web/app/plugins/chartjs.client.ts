/**
 * Chart.js plugin to register components once on app startup
 * This runs only on client-side
 */
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  LineController,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

export default defineNuxtPlugin(() => {
  // Register Chart.js components once
  Chart.register(
    CategoryScale,
    LinearScale,
    BarElement,
    BarController,
    LineElement,
    LineController,
    PointElement,
    Title,
    Tooltip,
    Legend,
  )
})
