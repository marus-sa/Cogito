<script setup>
import { computed, reactive, ref } from 'vue'
import { Check, CheckCheck, FilePlus2, Paperclip, Plus, Send, Star } from 'lucide-vue-next'
import { useHomeworkStore } from '../stores/homework'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'

const store = useHomeworkStore()
const auth = useAuthStore()
const messages = useMessagesStore()
const tab = ref('Все')
const createOpen = ref(false)
const submitOpen = ref(false)
const gradeOpen = ref(false)
const selected = ref(null)
const isTutor = computed(() => ['tutor', 'mentor', 'admin'].includes(auth.roleKey))
const form = reactive({ student: 'Анна Смирнова', title: '', subject: 'Математика', deadline: '7 августа', description: '', maxScore: 10 })
const grade = reactive({ score: 8, comment: 'Хорошая работа! Проверьте ещё раз пункт 7.' })
const filtered = computed(() => tab.value === 'Все' ? store.homework : store.homework.filter((item) => item.status === tab.value || (tab.value === 'Новые' && item.status === 'Новые')))
const statusClass = (status) => ({ 'Проверено': 'success', 'Просрочено': 'danger', 'В работе': 'warning', 'Сданы': 'purple' }[status] || 'gray')
async function create() {
  if (!form.title.trim()) {
    messages.showToast('Укажите название задания', 'error')
    return
  }

  try {
    await store.addHomework(form)
    createOpen.value = false
    form.title = ''
    form.description = ''
    messages.showToast('Домашнее задание создано')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
function submit(item) { selected.value = item; submitOpen.value = true }
async function sendWork() {
  try {
    await store.submitHomework(selected.value.id)
    submitOpen.value = false
    messages.showToast('Работа отправлена репетитору')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
function review(item) { selected.value = item; gradeOpen.value = true }
async function gradeWork() {
  try {
    await store.gradeHomework(selected.value.id, `${grade.score} / 10`)
    gradeOpen.value = false
    messages.showToast('Оценка и комментарий сохранены')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Домашние задания</h1><p>Все задания, сроки и обратная связь от репетитора.</p></div><BaseButton v-if="isTutor" @click="createOpen = true"><Plus :size="17" /> Задать домашнее задание</BaseButton></div>
    <section class="tabs"><button v-for="name in ['Все','Новые','В работе','Сданы','Проверено','Просрочено']" :key="name" :class="{ active: tab === name }" @click="tab = name">{{ name }} <span>{{ name === 'Все' ? store.homework.length : store.homework.filter(i => i.status === name).length }}</span></button></section>
    <section v-if="filtered.length" class="homework-grid"><article v-for="item in filtered" :key="item.id" class="homework-card card card-hover"><header><span :class="['tag', statusClass(item.status)]">{{ item.status }}</span><span v-if="item.score" class="score"><Star :size="13" /> {{ item.score }}</span></header><div class="subject-icon"><FilePlus2 :size="21" /></div><p class="subject">{{ item.subject }}</p><h2>{{ item.title }}</h2><p class="description">{{ item.description }}</p><div class="task-info"><span>Ученик <b>{{ item.student }}</b></span><span>Срок <b>{{ item.deadline }}</b></span></div><div class="card-footer"><span v-if="item.attachment" class="attachment"><Paperclip :size="13" /> {{ item.attachment }}</span><span v-else class="muted tiny">Без вложений</span><BaseButton v-if="isTutor && ['Сданы','В работе'].includes(item.status)" size="sm" @click="review(item)">Проверить</BaseButton><BaseButton v-else-if="!isTutor && item.status === 'В работе'" size="sm" @click="submit(item)">Сдать работу</BaseButton><button v-else class="view-button" @click="messages.showToast('Карточка задания открыта')">Подробнее</button></div></article></section><section v-else class="card"><EmptyState title="В этой категории пока нет заданий" text="Попробуйте выбрать другую вкладку или создайте новое задание." /></section>
    <BaseModal v-model="createOpen" title="Новое домашнее задание" wide><div class="form-grid"><div class="field"><label>Ученик</label><select v-model="form.student"><option>Анна Смирнова</option><option>Данил Мельников</option><option>Полина Кравцова</option></select></div><div class="field"><label>Предмет</label><input v-model="form.subject" /></div><div class="field full"><label>Название</label><input v-model="form.title" placeholder="Например, задачи на линейные уравнения" /></div><div class="field full"><label>Описание</label><textarea v-model="form.description" placeholder="Объясните, что нужно сделать…" /></div><div class="field"><label>Срок</label><input v-model="form.deadline" /></div><div class="field"><label>Максимальный балл</label><input v-model.number="form.maxScore" type="number" min="1" max="100" /></div><div class="file-box field full"><label><Paperclip :size="17" /> Прикрепить файл или ссылку<input type="file" /></label><small>В прототипе файл не загружается — можно выбрать его для отображения.</small></div></div><template #footer><BaseButton variant="outline" @click="createOpen = false">Отмена</BaseButton><BaseButton @click="create">Создать задание</BaseButton></template></BaseModal>
    <BaseModal v-model="submitOpen" title="Сдать домашнее задание"><p class="modal-copy">Оставьте комментарий репетитору и приложите выполненную работу.</p><div class="field"><label>Комментарий</label><textarea placeholder="Например, мне было сложно с заданием 8…" /></div><label class="upload-field"><Paperclip :size="19" /><span><b>Прикрепить файл</b><small>Фото, PDF или документ</small></span><input type="file" /></label><template #footer><BaseButton variant="outline" @click="submitOpen = false">Отмена</BaseButton><BaseButton @click="sendWork"><Send :size="15" /> Отправить</BaseButton></template></BaseModal>
    <BaseModal v-model="gradeOpen" title="Проверить работу"><p class="modal-copy">{{ selected?.title }} · {{ selected?.student }}</p><div class="form-grid"><div class="field"><label>Балл из 10</label><input v-model.number="grade.score" type="number" min="0" max="10" /></div><div class="field"><label>Решение</label><select><option>Принять работу</option><option>Вернуть на доработку</option></select></div><div class="field full"><label>Комментарий ученику</label><textarea v-model="grade.comment" /></div></div><template #footer><BaseButton variant="outline" @click="gradeOpen = false">Отмена</BaseButton><BaseButton @click="gradeWork"><CheckCheck :size="16" /> Сохранить проверку</BaseButton></template></BaseModal>
  </div>
</template>
<style scoped>
.tabs{display:flex;gap:6px;overflow-x:auto;margin-bottom:19px;padding-bottom:2px}.tabs button{display:inline-flex;align-items:center;gap:6px;min-height:35px;padding:0 11px;border:1px solid var(--border);border-radius:10px;color:var(--text-secondary);background:#fff;font-size:11px;font-weight:800;white-space:nowrap}.tabs button span{display:grid;place-items:center;min-width:17px;height:17px;padding:0 3px;background:#f2eff5;border-radius:6px;font-size:9px}.tabs button.active{color:var(--primary-dark);border-color:#cfc1ed;background:var(--primary-extra-light)}.tabs button.active span{color:#fff;background:var(--primary)}.homework-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:17px}.homework-card{display:flex;flex-direction:column;min-height:298px;padding:18px}.homework-card header{display:flex;align-items:center;justify-content:space-between}.score{display:flex;align-items:center;gap:3px;color:#a77a32;font-size:11px;font-weight:800}.subject-icon{display:grid;place-items:center;width:41px;height:41px;margin-top:18px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:13px}.subject{margin:12px 0 4px;color:var(--primary-dark);font-size:10px;font-weight:800}.homework-card h2{margin:0;font-size:14px;line-height:1.35}.description{display:-webkit-box;min-height:38px;margin:8px 0;color:var(--text-secondary);font-size:10px;line-height:1.55;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.task-info{display:grid;gap:5px;margin-top:auto;padding:10px 0;border-top:1px solid var(--border);color:var(--text-secondary);font-size:10px}.task-info b{color:var(--text-main)}.card-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;padding-top:10px}.attachment{display:flex;align-items:center;max-width:54%;gap:3px;overflow:hidden;color:var(--text-secondary);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.view-button{border:0;color:var(--primary-dark);background:transparent;font-size:10px;font-weight:800}.file-box{padding:12px;border:1px dashed #cfc2e8;border-radius:12px;background:#fbf9ff}.file-box label,.upload-field{display:flex;align-items:center;gap:8px;color:var(--primary-dark);font-size:11px;font-weight:800;cursor:pointer}.file-box input,.upload-field input{display:none}.file-box small{display:block;margin-top:5px;color:var(--text-secondary);font-size:9px}.modal-copy{margin:0 0 16px;color:var(--text-secondary);font-size:12px}.upload-field{margin-top:15px;padding:13px;border:1px dashed #cfc2e8;border-radius:12px;background:#fbf9ff}.upload-field b,.upload-field small{display:block}.upload-field small{margin-top:2px;color:var(--text-secondary);font-size:10px}@media(max-width:1050px){.homework-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:570px){.homework-grid{grid-template-columns:1fr}.homework-card{min-height:270px}}
</style>
