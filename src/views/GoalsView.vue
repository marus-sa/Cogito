<script setup>
import { computed, reactive, ref } from 'vue'
import { Award, CalendarDays, Check, CheckCircle2, Plus, Target } from 'lucide-vue-next'
import { useHomeworkStore } from '../stores/homework'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import ProgressBar from '../components/ProgressBar.vue'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'

const store = useHomeworkStore()
const auth = useAuthStore()
const messages = useMessagesStore()
const modalOpen = ref(false)
const canAdd = computed(() => ['student', 'tutor', 'mentor', 'admin'].includes(auth.roleKey))
const form = reactive({ title: '', subject: '', deadline: '', description: '', tasksText: '' })
const progress = (goal) => goal.tasks.length ? Math.round(goal.tasks.filter((task) => task.done).length / goal.tasks.length * 100) : 0
async function addGoal() {
  if (!form.title.trim()) {
    messages.showToast('Добавьте название цели', 'error')
    return
  }

  const tasks = form.tasksText
    .split('\n')
    .filter(Boolean)
    .map((label, index) => ({ id: index + 1, label, done: false }))

  try {
    await store.addGoal({ ...form, tasks })
    modalOpen.value = false
    form.title = ''
    form.subject = ''
    form.deadline = ''
    form.description = ''
    form.tasksText = ''
    messages.showToast('Учебная цель добавлена')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function toggle(goal, task) {
  try {
    await store.toggleGoalTask(goal.id, task.id)
    if (progress(goal) === 100) messages.showToast('Цель выполнена! Вы проделали отличную работу.')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Учебные цели</h1><p>Большие результаты складываются из маленьких понятных шагов.</p></div><BaseButton v-if="canAdd" @click="modalOpen = true"><Plus :size="17" /> Добавить цель</BaseButton></div>
    <section class="goal-list"><article v-for="goal in store.goals" :key="goal.id" class="goal-full card"><header><span class="goal-icon"><Target :size="22" /></span><div><span class="tag">{{ goal.subject }}</span><h2>{{ goal.title }}</h2><p>{{ goal.description }}</p></div><div class="goal-status"><b>{{ progress(goal) }}%</b><span>выполнено</span></div></header><div class="goal-progress"><ProgressBar :value="progress(goal)" :show-label="false" /><div><span><CalendarDays :size="13" /> Срок: {{ goal.deadline }}</span><span>Репетитор: <b>{{ goal.tutor }}</b></span></div></div><div class="tasks"><div class="tasks-head"><h3>Подзадачи</h3><span>{{ goal.tasks.filter(t => t.done).length }} из {{ goal.tasks.length }}</span></div><button v-for="task in goal.tasks" :key="task.id" class="task" :class="{ done: task.done }" @click="toggle(goal, task)"><i><Check v-if="task.done" :size="14" /></i><span>{{ task.label }}</span><CheckCircle2 v-if="task.done" :size="16" /></button><div v-if="goal.tasks.length === 0" class="no-tasks">Добавьте подзадачи, чтобы отслеживать путь к цели.</div></div><footer v-if="progress(goal) === 100"><span><Award :size="17" /> Цель завершена</span><p>Вы последовательно шли вперёд — это важный результат.</p></footer></article></section>
    <BaseModal v-model="modalOpen" title="Новая учебная цель" wide><div class="form-grid"><div class="field full"><label>Название цели</label><input v-model="form.title" placeholder="Например, повысить оценку с 3 до 4" /></div><div class="field"><label>Предмет</label><input v-model="form.subject" placeholder="Например, математика" /></div><div class="field"><label>Срок</label><input v-model="form.deadline" placeholder="Например, 25 августа" /></div><div class="field full"><label>Измеримый результат и описание</label><textarea v-model="form.description" placeholder="Как будет выглядеть достигнутый результат?" /></div><div class="field full"><label>Подзадачи и контрольные точки</label><textarea v-model="form.tasksText" placeholder="Каждая подзадача с новой строки\nПовторить дроби\nВыполнить итоговый тест" /></div></div><template #footer><BaseButton variant="outline" @click="modalOpen = false">Отмена</BaseButton><BaseButton @click="addGoal">Создать цель</BaseButton></template></BaseModal>
  </div>
</template>
<style scoped>
.goal-list{display:grid;gap:17px}.goal-full{overflow:hidden}.goal-full>header{display:flex;align-items:flex-start;gap:14px;padding:23px 24px 18px}.goal-icon{display:grid;place-items:center;width:47px;height:47px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:15px}.goal-full header>div:nth-child(2){min-width:0;flex:1}.goal-full h2{margin:7px 0 4px;font-size:18px;letter-spacing:-.35px}.goal-full p{max-width:650px;margin:0;color:var(--text-secondary);font-size:11px;line-height:1.6}.goal-status{display:grid;justify-items:end;padding:4px 0 0 10px}.goal-status b{font-size:25px;letter-spacing:-1px}.goal-status span{color:var(--text-secondary);font-size:10px}.goal-progress{padding:14px 24px;background:#fcfbfe;border-top:1px solid var(--border);border-bottom:1px solid var(--border)}.goal-progress>div:last-child{display:flex;justify-content:space-between;gap:13px;margin-top:9px;color:var(--text-secondary);font-size:10px}.goal-progress>div:last-child span{display:flex;align-items:center;gap:4px}.goal-progress b{color:var(--text-main)}.tasks{padding:18px 24px}.tasks-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.tasks-head h3{margin:0;font-size:13px}.tasks-head span{color:var(--text-secondary);font-size:10px}.task{display:flex;align-items:center;gap:10px;width:100%;min-height:38px;padding:4px 0;border:0;border-bottom:1px solid #f0edf4;color:var(--text-main);background:#fff;text-align:left;font-size:11px}.task:last-of-type{border-bottom:0}.task i{display:grid;place-items:center;width:19px;height:19px;border:1px solid #cbc4d4;border-radius:6px;font-style:normal}.task.done{color:var(--text-secondary);text-decoration:line-through}.task.done i{color:#fff;border-color:#76b394;background:#76b394}.task :deep(svg:last-child){margin-left:auto;color:#65a681}.no-tasks{padding:15px;color:var(--text-secondary);font-size:11px;text-align:center}.goal-full footer{display:flex;align-items:center;gap:10px;padding:12px 24px;color:#488663;background:#eaf6ef}.goal-full footer span{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:800}.goal-full footer p{margin-left:auto;color:#5d8d70;font-size:10px}@media(max-width:600px){.goal-full>header{padding:18px;gap:10px}.goal-status{display:none}.goal-progress,.tasks{padding-left:18px;padding-right:18px}.goal-progress>div:last-child{display:block;line-height:1.9}.goal-full footer{align-items:flex-start;flex-direction:column;padding:12px 18px}.goal-full footer p{margin:0}.goal-full h2{font-size:15px}}
</style>
