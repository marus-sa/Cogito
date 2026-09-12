<script setup>
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Check, GraduationCap, HeartHandshake, ShieldCheck, UserRoundCheck, UsersRound } from 'lucide-vue-next'
import { roles } from '../data/mockData'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const step = ref(1)
const selectedRole = ref('student')
const form = reactive({ firstName: '', lastName: '', email: '', password: '', confirm: '', consent: false, grade: '7', subject: 'Математика', days: 'Пн, Ср', time: 'После 17:00', about: '', child: 'Анна Смирнова', direction: 'Образовательное направление', tutors: 'Мария Иванова' })
const error = ref('')
const waitingApproval = ref(false)
const publicRoles = ['student', 'tutor', 'parent']
const roleCards = [
  ['student', GraduationCap], ['tutor', UserRoundCheck], ['parent', UsersRound], ['mentor', HeartHandshake], ['admin', ShieldCheck],
]
const currentRole = computed(() => roles[selectedRole.value])
function selectRole(key) {
  if (!publicRoles.includes(key)) {
    error.value = 'Наставников и администраторов добавляет глава проекта по приглашению.'
    return
  }
  error.value = ''
  selectedRole.value = key
}
function next() {
  error.value = ''
  if (step.value === 2 && (!form.firstName || !form.lastName || !/^\S+@\S+\.\S+$/.test(form.email) || form.password.length < 6 || form.password !== form.confirm || !form.consent)) { error.value = 'Заполните все обязательные поля: укажите корректную почту, пароль от 6 символов и согласие.'; return }
  step.value++
}
async function finish() {
  error.value = ''

  try {
    const result = await auth.register({
      ...form,
      role: selectedRole.value,
      subjects: form.subject,
    })
    waitingApproval.value = result.needsApproval
    step.value = 4
  } catch (requestError) {
    error.value = requestError.message
  }
}
function toAccount() { router.push(waitingApproval.value ? '/login' : '/dashboard') }
</script>
<template>
  <div class="register-page"><header><RouterLink to="/login" class="back"><ArrowLeft :size="17" /> К входу</RouterLink><RouterLink class="mini-brand" to="/login"><span>✦</span><b>Cogito</b><small>Light Hearts</small></RouterLink></header>
    <main class="register-card">
      <div class="steps" aria-label="Шаги регистрации"><span v-for="n in 4" :key="n" :class="{ active: step >= n, current: step === n }"><i>{{ step > n ? '✓' : n }}</i><b>{{ ['Роль', 'Данные', 'Подробнее', 'Готово'][n - 1] }}</b></span></div>
      <section v-if="step === 1"><div class="intro"><span class="eyebrow">Создание аккаунта</span><h1>Выберите вашу роль</h1><p>Ученик и родитель получают доступ сразу. Заявку репетитора подтверждает команда проекта.</p></div><div class="role-cards"><button v-for="[key, icon] in roleCards" :key="key" type="button" :class="{ chosen: selectedRole === key, locked: !publicRoles.includes(key) }" @click="selectRole(key)"><component :is="icon" :size="23" /><strong>{{ roles[key].label }}</strong><small>{{ publicRoles.includes(key) ? roles[key].description : 'Только по приглашению' }}</small><i><Check v-if="selectedRole === key" :size="14" /></i></button></div></section>
      <section v-else-if="step === 2"><div class="intro"><span class="eyebrow">Шаг 2 из 4</span><h1>Расскажите о себе</h1><p>Эти данные помогут команде Light Hearts поддерживать вас.</p></div><div class="form-grid"><div class="field"><label>Имя</label><input v-model.trim="form.firstName" placeholder="Например, Анна" /></div><div class="field"><label>Фамилия</label><input v-model.trim="form.lastName" placeholder="Смирнова" /></div><div class="field full"><label>Электронная почта</label><input v-model.trim="form.email" type="email" placeholder="anna@example.ru" /></div><div class="field"><label>Пароль</label><input v-model="form.password" type="password" placeholder="Не менее 6 символов" /></div><div class="field"><label>Повторите пароль</label><input v-model="form.confirm" type="password" placeholder="Повторите пароль" /></div></div><label class="consent"><input v-model="form.consent" type="checkbox" /> <span>Я согласен(-на) на обработку персональных данных</span></label></section>
      <section v-else-if="step === 3"><div class="intro"><span class="eyebrow">Шаг 3 из 4</span><h1>Немного подробностей</h1><p>Данные можно будет изменить в профиле.</p></div><div v-if="selectedRole === 'student' || selectedRole === 'tutor'" class="form-grid"><div class="field"><label>Класс</label><select v-model="form.grade"><option v-for="grade in [5,6,7,8,9,10,11]" :key="grade">{{ grade }}</option></select></div><div class="field"><label>{{ selectedRole === 'tutor' ? 'Предметы преподавания' : 'Предмет' }}</label><input v-model="form.subject" placeholder="Математика" /></div><div class="field"><label>Удобные дни</label><input v-model="form.days" /></div><div class="field"><label>Удобное время</label><input v-model="form.time" /></div><div v-if="selectedRole === 'tutor'" class="field full"><label>Кратко о себе</label><textarea v-model="form.about" placeholder="Расскажите, почему вам важно преподавать…" /></div></div><div v-else-if="selectedRole === 'parent'" class="form-grid"><div class="field full"><label>Ребёнок или код ребёнка</label><select v-model="form.child"><option>Анна Смирнова</option><option>У меня есть код ребёнка</option></select></div></div><div v-else class="form-grid"><div class="field"><label>Направление работы</label><input v-model="form.direction" /></div><div class="field"><label>Закреплённые репетиторы</label><input v-model="form.tutors" /></div></div></section>
      <section v-else class="success"><div><Check :size="30" /></div><span class="eyebrow">Регистрация завершена</span><h1>{{ waitingApproval ? 'Заявка отправлена!' : 'Добро пожаловать в Cogito!' }}</h1><p v-if="waitingApproval">Команда Light Hearts проверит заявку репетитора. После подтверждения вы сможете войти в личный кабинет.</p><p v-else>Ваш кабинет <b>«{{ currentRole.label }}»</b> уже готов. Начните с главной страницы — там собраны все важные дела.</p><button class="primary-action" @click="toAccount">{{ waitingApproval ? 'Вернуться ко входу' : 'Перейти в личный кабинет' }} <ArrowRight :size="17" /></button></section>
      <p v-if="error" class="form-error">{{ error }}</p>
      <footer v-if="step < 4"><button v-if="step > 1" class="secondary-action" @click="step--"><ArrowLeft :size="16" /> Назад</button><span></span><button class="primary-action" @click="step === 3 ? finish() : next()">{{ step === 3 ? 'Завершить регистрацию' : 'Продолжить' }} <ArrowRight :size="16" /></button></footer>
    </main>
  </div>
</template>
<style scoped>
.register-page { min-height: 100vh; padding: 24px; background: linear-gradient(135deg,#f8f5fc,#f1ecfb); }.register-page > header { display:flex;align-items:center;justify-content:space-between;max-width:900px;margin:0 auto 24px; }.back { display:inline-flex;align-items:center;gap:6px;color:var(--primary-dark);font-size:12px;font-weight:800; }.mini-brand { display:flex;align-items:baseline;gap:5px;color:var(--text-main); }.mini-brand span { color:var(--primary);font-size:18px; }.mini-brand b{font-size:17px;letter-spacing:-.5px}.mini-brand small{color:var(--text-secondary);font-size:9px;font-weight:700}.register-card{width:min(100%,900px);min-height:590px;margin:auto;padding:30px 54px;background:#fff;border:1px solid var(--border);border-radius:24px;box-shadow:var(--shadow)}.steps{display:flex;justify-content:space-between;max-width:570px;margin:0 auto 35px}.steps span{position:relative;display:grid;justify-items:center;gap:6px;min-width:70px;color:#a29aa9;font-size:10px;font-weight:800}.steps span:not(:last-child)::after{position:absolute;z-index:0;top:15px;left:calc(50% + 18px);width:calc(100% - 35px);height:2px;content:'';background:var(--border)}.steps i{position:relative;z-index:1;display:grid;place-items:center;width:31px;height:31px;border:1px solid var(--border);border-radius:50%;font-style:normal;background:#fff}.steps .active{color:var(--primary-dark)}.steps .active i{color:#fff;border-color:var(--primary);background:var(--primary)}.steps .active:not(:last-child)::after{background:var(--primary-light)}.intro{text-align:center}.eyebrow{display:inline-block;padding:5px 9px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:100px;font-size:10px;font-weight:800}.intro h1,.success h1{margin:11px 0 7px;font-size:28px;letter-spacing:-.8px}.intro p,.success p{margin:0;color:var(--text-secondary);font-size:13px;line-height:1.65}.role-cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:30px}.role-cards button{position:relative;display:grid;justify-items:center;gap:8px;min-height:174px;padding:18px 8px;border:1px solid var(--border);border-radius:17px;color:#716878;background:#fff;transition:.2s}.role-cards button:hover{border-color:#cdbcF0;transform:translateY(-2px)}.role-cards button.chosen{color:var(--primary-dark);border-color:var(--primary);background:#fbf9ff;box-shadow:0 8px 17px rgba(106,79,168,.12)}.role-cards button.locked{opacity:.62;background:#faf9fb}.role-cards button.locked:hover{transform:none}.role-cards strong{font-size:12px}.role-cards small{font-size:9px;line-height:1.4}.role-cards i{position:absolute;top:9px;right:9px;display:grid;place-items:center;width:19px;height:19px;border:1px solid var(--border);border-radius:50%;font-style:normal}.role-cards .chosen i{color:#fff;border-color:var(--primary);background:var(--primary)}.form-grid{margin-top:27px}.consent{display:flex;align-items:flex-start;gap:9px;margin-top:17px;color:var(--text-secondary);font-size:11px;line-height:1.45}.consent input{accent-color:var(--primary);margin-top:1px}.form-error{margin:16px 0 0;color:#ae5b5b;font-size:11px;text-align:center}.register-card footer{display:flex;align-items:center;justify-content:space-between;margin-top:30px;padding-top:20px;border-top:1px solid var(--border)}.primary-action,.secondary-action{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:40px;padding:0 14px;border-radius:11px;font-size:12px;font-weight:800}.primary-action{border:0;color:#fff;background:var(--primary)}.primary-action:hover{background:var(--primary-dark)}.secondary-action{border:1px solid var(--border);color:var(--text-secondary);background:#fff}.secondary-action:hover{color:var(--primary-dark);background:var(--primary-extra-light)}.success{max-width:470px;margin:55px auto;text-align:center}.success > div{display:grid;place-items:center;width:65px;height:65px;margin:0 auto 18px;color:#4e906a;background:#e8f5ee;border-radius:22px}.success p{margin:0 auto 23px}.success .primary-action{margin:auto}
@media(max-width:700px){.register-page{padding:14px}.register-card{min-height:0;padding:25px 18px}.steps{margin-bottom:25px}.steps b{display:none}.role-cards{grid-template-columns:repeat(2,1fr)}.role-cards button:last-child{grid-column:1/-1;min-height:115px}.intro h1,.success h1{font-size:24px}.success{margin:35px auto}.register-page>header{margin-bottom:16px}}@media(max-width:390px){.role-cards{gap:7px}.role-cards button{min-height:150px}.steps span{min-width:40px}}
</style>
