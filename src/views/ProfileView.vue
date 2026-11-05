<script setup>
import { computed, reactive, ref } from 'vue'
import { Clock3, Mail, Palette, Pencil, Save, UserRound } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import UserAvatar from '../components/UserAvatar.vue'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'

const auth = useAuthStore()
const messages = useMessagesStore()
const editing = ref(false)
const avatarOpen = ref(false)
const parts = auth.user.name.split(' ')
const form = reactive({
  firstName: parts[0],
  lastName: parts.slice(1).join(' '),
  email: auth.user.email || '',
  grade: auth.user.grade || '',
  subjects: auth.user.subjects || '',
  time: auth.user.availableTime || '',
})
const colors = ['#b39ddb', '#9ebad5', '#a8cdbb', '#e2b9c7', '#e6c48e', '#9fc9c7']
const details = computed(() => {
  let firstField = { label: 'Класс', value: form.grade || 'Не указан' }
  if (auth.roleKey === 'parent') {
    firstField = { label: 'Ребёнок', value: auth.user.childName || 'Не указан' }
  }
  const subjectLabel = auth.roleKey === 'tutor' ? 'Предметы' : 'Предмет'
  return [
    firstField,
    { label: subjectLabel, value: form.subjects || 'Не указан' },
    { label: 'Удобное время', value: form.time || 'Не указано' },
  ]
})
const avatarColor = computed(() => auth.user.avatarColor || auth.user.color)

async function save() {
  try {
    await auth.updateProfile({
      firstName: form.firstName,
      lastName: form.lastName,
      grade: form.grade,
      subjects: form.subjects,
      time: form.time,
    })
    editing.value = false
    messages.showToast('Изменения профиля сохранены')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function chooseAvatarColor(color) {
  try {
    await auth.updateProfile({ avatarColor: color })
    avatarOpen.value = false
    messages.showToast('Оформление аватара сохранено')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>Профиль</h1>
        <p>Ваши данные.</p>
      </div>
      <BaseButton v-if="!editing" variant="outline" @click="editing = true">
        <Pencil :size="16" />
        Редактировать
      </BaseButton>
      <BaseButton v-else @click="save">
        <Save :size="16" />
        Сохранить
      </BaseButton>
    </div>

    <div class="profile-grid">
      <section class="card profile-summary">
        <div class="cover"></div>
        <div class="person-block">
          <UserAvatar :initials="auth.user.initials" :color="avatarColor" :size="78" />
          <button
            class="avatar-edit"
            type="button"
            aria-label="Оформить аватар"
            title="Оформить аватар"
            @click="avatarOpen = true"
          >
            <Palette :size="13" />
          </button>
          <h2>{{ auth.user.name }}</h2>
          <span class="tag">{{ auth.roleLabel }}</span>
          <p>{{ auth.user.description }}</p>
        </div>
        <div class="profile-contact">
          <span>
            <Mail :size="15" />
            {{ form.email }}
          </span>
          <span>
            <Clock3 :size="15" />
            {{ form.time }}
          </span>
        </div>
      </section>

      <section class="card panel">
        <div class="section-title">
          <h2>Основные данные</h2>
          <UserRound :size="18" class="accent" />
        </div>
        <div v-if="editing" class="form-grid">
          <div class="field">
            <label>Имя</label>
            <input v-model.trim="form.firstName" />
          </div>
          <div class="field">
            <label>Фамилия</label>
            <input v-model.trim="form.lastName" />
          </div>
          <div class="field full">
            <label>Email</label>
            <input :value="form.email" type="email" disabled />
            <small class="field-note">
              Смену почты выполняет координатор после проверки нового адреса.
            </small>
          </div>
          <div class="field">
            <label>Класс</label>
            <input v-model.trim="form.grade" />
          </div>
          <div class="field">
            <label>Предметы</label>
            <input v-model.trim="form.subjects" />
          </div>
          <div class="field full">
            <label>Удобное время</label>
            <input v-model.trim="form.time" />
          </div>
        </div>
        <div v-else class="details">
          <div v-for="detail in details" :key="detail.label">
            <span>{{ detail.label }}</span>
            <b>{{ detail.value }}</b>
          </div>
        </div>
      </section>
    </div>

    <BaseModal v-model="avatarOpen" title="Оформление аватара">
      <p class="modal-copy">
        Выберите цвет для своего аватара. Фотографии не хранятся в приложении, поэтому личные данные
        остаются защищёнными.
      </p>
      <div class="avatar-choices">
        <button
          v-for="color in colors"
          :key="color"
          type="button"
          :class="{ chosen: avatarColor === color }"
          :style="{ background: color }"
          :aria-label="`Выбрать цвет ${color}`"
          @click="chooseAvatarColor(color)"
        >
          <span v-if="avatarColor === color">✓</span>
        </button>
      </div>
      <template #footer>
        <BaseButton variant="outline" @click="avatarOpen = false">Закрыть</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: minmax(270px, 0.8fr) minmax(360px, 1.2fr);
  gap: 19px;
}
.profile-summary {
  overflow: hidden;
  text-align: center;
}
.cover {
  height: 85px;
  background: linear-gradient(135deg, #e2d7f7, #cbb9ef);
}
.person-block {
  position: relative;
  padding: 0 22px 20px;
}
.person-block :deep(.avatar) {
  margin-top: -39px;
  box-shadow: 0 0 0 5px #fff;
}
.person-block h2 {
  margin: 11px 0 6px;
  font-size: 18px;
}
.person-block p {
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 10px;
}
.avatar-edit {
  position: absolute;
  top: 13px;
  left: calc(50% + 25px);
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border: 2px solid #fff;
  border-radius: 50%;
  color: #fff;
  background: var(--primary);
}
.avatar-edit:hover {
  background: var(--primary-dark);
}
.profile-contact {
  display: grid;
  gap: 10px;
  padding: 15px 21px;
  border-top: 1px solid var(--border);
  text-align: left;
}
.profile-contact span {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 10px;
}
.accent {
  color: var(--primary);
}
.details {
  display: grid;
  gap: 16px;
  padding-top: 3px;
}
.details > div {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.details > div:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}
.details span,
.details b {
  display: block;
}
.details span {
  color: var(--text-secondary);
  font-size: 10px;
}
.details b {
  margin-top: 4px;
  font-size: 12px;
}
.field-note {
  display: block;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 1.4;
}
.modal-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.avatar-choices {
  display: flex;
  flex-wrap: wrap;
  gap: 13px;
  margin-top: 20px;
}
.avatar-choices button {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 3px solid #fff;
  border-radius: 50%;
  color: #fff;
  box-shadow: 0 0 0 1px var(--border);
}
.avatar-choices button.chosen {
  box-shadow: 0 0 0 3px var(--primary);
}
@media (max-width: 720px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
  .profile-summary {
    max-width: none;
  }
}
</style>
