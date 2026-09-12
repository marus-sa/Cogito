<script setup>
import { computed, ref } from 'vue'
import { BookOpen, CalendarDays, CheckCircle2, Sparkles, Target, TrendingUp } from 'lucide-vue-next'
import { useHomeworkStore } from '../stores/homework'
import StatCard from '../components/StatCard.vue'
import PerformanceChart from '../components/PerformanceChart.vue'
import ProgressBar from '../components/ProgressBar.vue'

const store = useHomeworkStore()
const subject = ref('Математика')
const period = ref('За 6 недель')
const goal = computed(() => store.goals[0])
const goalProgress = computed(() => Math.round(goal.value.tasks.filter((item) => item.done).length / goal.value.tasks.length * 100))
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Прогресс и успеваемость</h1><p>Понятная картина результатов и зон, которым нужно больше внимания.</p></div><div class="filters"><select v-model="subject"><option>Математика</option><option>Информатика</option></select><select v-model="period"><option>За 6 недель</option><option>За месяц</option><option>За четверть</option></select></div></div>
    <section class="grid four-col"><StatCard label="Средний балл" value="4,1" detail="+0,6" icon="TrendingUp" tone="green" /><StatCard label="Выполнено заданий" value="82%" icon="CheckCircle2" /><StatCard label="Проведено занятий" value="12" icon="CalendarDays" tone="orange" /><StatCard label="Прогресс по цели" :value="`${goalProgress}%`" icon="Target" tone="rose" /></section>
    <div class="grid two-col below"><section class="card panel"><div class="section-title"><div><h2>Динамика баллов</h2><p class="muted tiny">{{ subject }} · {{ period }}</p></div><span class="tag success">Рост</span></div><PerformanceChart :values="[48,60,58,69,67,76]" :labels="['1 июл','8 июл','15 июл','22 июл','29 июл','сегодня']" /><div class="chart-hint"><span><i></i> Оценка за работу</span><b>Текущий результат: 4</b></div></section><section class="card panel"><div class="section-title"><h2>Цель на четверть</h2><span class="tag">{{ goalProgress }}%</span></div><h3>{{ goal.title }}</h3><p class="muted tiny goal-copy">Срок: {{ goal.deadline }} · с Марией Ивановой</p><ProgressBar :value="goalProgress" /><div class="goal-points"><span v-for="task in goal.tasks" :key="task.id" :class="{ done: task.done }"><i></i>{{ task.label }}</span></div></section></div>
    <div class="grid two-col below"><section class="card panel"><div class="section-title"><h2>Освоенные темы</h2><BookOpen :size="18" class="light-icon" /></div><div class="skills"><div><b>Обыкновенные дроби</b><span>Уверенно</span></div><div><b>Проценты</b><span>Уверенно</span></div><div><b>Линейные уравнения</b><span class="process">В работе</span></div></div></section><section class="card panel"><div class="section-title"><h2>Комментарий репетитора</h2><Sparkles :size="18" class="light-icon" /></div><p class="teacher-note">Анна стала внимательнее проверять решение и увереннее объясняет ход мысли. Следующий фокус — больше практики с уравнениями.</p><span class="note-date">Мария Иванова · 30 июля</span></section></div>
  </div>
</template>
<style scoped>
.filters{display:flex;gap:8px}.filters select{min-height:39px;padding:0 30px 0 10px;border:1px solid var(--border);border-radius:10px;color:#655b72;background:#fff;font-size:11px;font-weight:700}.below{margin-top:19px}.section-title p{margin:3px 0 0}.chart-hint{display:flex;justify-content:space-between;margin:15px 10px 0;color:var(--text-secondary);font-size:10px}.chart-hint i{display:inline-block;width:8px;height:8px;background:var(--primary);border-radius:50%}.goal-copy{margin:4px 0 17px}.goal-points{display:grid;gap:10px;margin-top:18px}.goal-points span{display:flex;align-items:center;gap:7px;color:var(--text-secondary);font-size:10px}.goal-points i{width:8px;height:8px;border:1px solid #c8c0d1;border-radius:50%}.goal-points .done{color:var(--text-main)}.goal-points .done i{border-color:#75b798;background:#75b798}.skills{display:grid;gap:11px}.skills>div{display:flex;align-items:center;justify-content:space-between;padding-bottom:10px;border-bottom:1px solid var(--border)}.skills>div:last-child{border-bottom:0;padding-bottom:0}.skills b{font-size:11px}.skills span{padding:4px 7px;color:#4c8666;background:#e8f5ee;border-radius:100px;font-size:9px;font-weight:800}.skills span.process{color:#a77a32;background:#fcf4e5}.light-icon{color:var(--primary);}.teacher-note{margin:8px 0 14px;padding-left:12px;border-left:3px solid #d8cdf1;color:#5f556b;font-size:11px;line-height:1.7}.note-date{color:var(--text-secondary);font-size:10px}@media(max-width:720px){.filters{margin-top:14px}.filters select{flex:1;min-width:0}.chart-hint{display:block;line-height:1.8}}
</style>
