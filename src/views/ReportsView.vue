<script setup>
import { onMounted, ref } from 'vue'
import { Check, Download, FileBarChart, FileText, UsersRound } from 'lucide-vue-next'
import { useMessagesStore } from '../stores/messages'
import { api } from '../api'
import StatCard from '../components/StatCard.vue'
import PerformanceChart from '../components/PerformanceChart.vue'
import BaseButton from '../components/BaseButton.vue'
const messages = useMessagesStore()
const pendingTutors = ref([])
function download(name) { messages.showToast(`Отчёт «${name}» подготовлен к скачиванию`) }
async function loadApplications() {
  try {
    const data = await api('/admin/users?status=pending')
    pendingTutors.value = data.items.filter((user) => user.role === 'tutor')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
async function approve(user) {
  try {
    await api(`/admin/users/${user.id}`, { method: 'PATCH', body: JSON.stringify({ accountStatus: 'active' }) })
    pendingTutors.value = pendingTutors.value.filter((item) => item.id !== user.id)
    messages.showToast(`Заявка ${user.name} подтверждена`)
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
onMounted(loadApplications)
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Отчёты проекта</h1><p>Статистика Light Hearts для координации и принятия решений.</p></div><BaseButton @click="download('Общий отчёт за август')"><Download :size="16" /> Скачать отчёт</BaseButton></div>
    <section class="grid four-col"><StatCard label="Выполнено заданий" value="78%" detail="+5% за месяц" icon="FileBarChart" /><StatCard label="Активных участников" value="148" icon="UsersRound" tone="green" /><StatCard label="Проверка занятий" value="94%" icon="FileText" tone="orange" /><StatCard label="Средняя оценка" value="4,2" icon="TrendingUp" tone="rose" /></section>
    <section class="card panel below"><div class="section-title"><h2>Заявки репетиторов</h2><span class="tag warning">{{ pendingTutors.length }} ожидают</span></div><div v-if="pendingTutors.length" class="applications"><article v-for="user in pendingTutors" :key="user.id"><span><UsersRound :size="17" /></span><div><b>{{ user.name }}</b><small>{{ user.email }} · {{ user.subjects || 'Предмет не указан' }}</small></div><BaseButton size="sm" @click="approve(user)"><Check :size="15" /> Подтвердить</BaseButton></article></div><p v-else class="muted tiny">Новых заявок на проверку нет.</p></section>
    <div class="grid two-col below"><section class="card panel"><div class="section-title"><h2>Активность пользователей</h2><span class="tag success">Стабильный рост</span></div><PerformanceChart :values="[42,51,47,63,67,75]" :labels="['март','апрель','май','июнь','июль','август']" /><p class="muted tiny report-note">Количество активных участников за последние 6 месяцев.</p></section><section class="card panel"><div class="section-title"><h2>Готовые отчёты</h2><span class="muted tiny">Обновлено сегодня</span></div><button v-for="item in ['Волонтёрские часы · июль','Успеваемость учеников · июль','Качество занятий · июль']" :key="item" class="report-file" @click="download(item)"><span><FileText :size="18" /></span><b>{{ item }}</b><Download :size="16" /></button></section></div>
    <section class="card panel below"><div class="section-title"><h2>Сводка по предметам</h2><span class="muted tiny">Август 2026</span></div><div class="table-wrap"><table><thead><tr><th>Предмет</th><th>Учеников</th><th>Репетиторов</th><th>Занятий</th><th>Средний прогресс</th></tr></thead><tbody><tr><td><b>Математика</b></td><td>47</td><td>20</td><td>158</td><td><span class="tag success">71%</span></td></tr><tr><td><b>Русский язык</b></td><td>29</td><td>13</td><td>91</td><td><span class="tag success">68%</span></td></tr><tr><td><b>Английский язык</b></td><td>18</td><td>8</td><td>47</td><td><span class="tag warning">61%</span></td></tr><tr><td><b>Информатика</b></td><td>8</td><td>5</td><td>22</td><td><span class="tag success">74%</span></td></tr></tbody></table></div></section>
  </div>
</template>
<style scoped>
.below{margin-top:19px}.report-note{margin:8px 10px 0}.applications{display:grid}.applications article{display:flex;align-items:center;gap:9px;padding:12px 0;border-top:1px solid var(--border)}.applications article>span{display:grid;place-items:center;width:34px;height:34px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:10px}.applications article>div{min-width:0;flex:1}.applications b,.applications small{display:block}.applications b{font-size:11px}.applications small{margin-top:3px;overflow:hidden;color:var(--text-secondary);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.report-file{display:flex;align-items:center;gap:9px;width:100%;padding:12px 0;border:0;border-top:1px solid var(--border);color:var(--text-main);background:#fff;text-align:left}.report-file>span{display:grid;place-items:center;width:34px;height:34px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:10px}.report-file b{flex:1;font-size:11px}.report-file>svg{color:var(--text-secondary)}.report-file:hover b{color:var(--primary-dark)}
</style>
