<script setup>
import {
  Bell,
  BookOpenCheck,
  CalendarClock,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  FileBarChart,
  FileVideo,
  GraduationCap,
  LayoutDashboard,
  MessageCircle,
  MessagesSquare,
  Sparkles,
  Target,
  TrendingUp,
  UserRound,
  UsersRound,
} from 'lucide-vue-next'

defineProps({ name: String, size: { type: Number, default: 19 } })

// Здесь перечислены только иконки, которые нужны приложению.
const icons = {
  Bell,
  BookOpenCheck,
  CalendarClock,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  FileBarChart,
  FileVideo,
  GraduationCap,
  LayoutDashboard,
  MessageCircle,
  MessagesSquare,
  Sparkles,
  Target,
  TrendingUp,
  UserRound,
  UsersRound,
}
</script>

<template>
  <component :is="icons[name] || Bell" :size="size" />
</template>
