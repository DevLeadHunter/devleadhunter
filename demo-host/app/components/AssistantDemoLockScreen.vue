<template>
  <div class="lock">
    <div class="lock__clock">
      <span class="lock__date">{{ props.dateLabel }}</span>
      <span class="lock__time">{{ props.time }}</span>
    </div>

    <div class="lock__stack">
      <span v-if="props.isExample" class="lock__example">exemple</span>
      <div class="lock__notification" :class="{ 'lock__notification--new': !props.isExample }" aria-live="polite">
        <div class="lock__app" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path
              d="M12 3C6.5 3 2.5 6.6 2.5 11c0 2.4 1.2 4.6 3.2 6.1L5 21l4.4-2.1c.8.2 1.7.3 2.6.3 5.5 0 9.5-3.6 9.5-8.1S17.5 3 12 3Z"
              fill="#fff"
            />
          </svg>
        </div>
        <div class="lock__body">
          <div class="lock__top">
            <span class="lock__title">{{ props.assistantName }} · réceptionniste</span>
            <span class="lock__when">maintenant</span>
          </div>
          <p class="lock__text">{{ props.alertText }}</p>
        </div>
      </div>
      <p class="lock__hint">{{ props.hintText }}</p>
    </div>

    <div class="lock__controls" aria-hidden="true">
      <span class="lock__control">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
          <path d="M8 3h8l1 4-2 3v11H9V10L7 7z" />
          <path d="M9 10h6" />
        </svg>
      </span>
      <span class="lock__home" />
      <span class="lock__control">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
          <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
          <circle cx="12" cy="13" r="3" />
        </svg>
      </span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { AssistantDemoLockScreenProps } from '~/types/AssistantDemoLockScreen'

const props: AssistantDemoLockScreenProps = defineProps({
  time: {
    type: String,
    required: true,
  },
  dateLabel: {
    type: String,
    required: true,
  },
  assistantName: {
    type: String,
    required: true,
  },
  alertText: {
    type: String,
    required: true,
  },
  isExample: {
    type: Boolean,
    default: true,
  },
  hintText: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.lock {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 52px 12px 10px;
  color: #fff;
  font-family: var(--ia-font-b);
}
.lock__clock {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.lock__date {
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.01em;
  opacity: 0.92;
}
.lock__time {
  font-size: 82px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.25);
}
.lock__stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 8px;
}
.lock__example {
  align-self: flex-end;
  margin-right: 6px;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.55;
}
.lock__notification {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  color: #111;
  padding: 12px 14px 13px 12px;
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 11px;
  align-items: start;
  box-shadow: 0 18px 40px -18px rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(16px);
}
.lock__notification--new {
  animation: lock-drop 0.45s cubic-bezier(0.2, 0.7, 0.3, 1);
}
@keyframes lock-drop {
  from {
    transform: translateY(18px);
    opacity: 0;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
.lock__app {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(180deg, #67e07a, #2fb648);
  display: grid;
  place-items: center;
}
.lock__app svg {
  width: 24px;
  height: 24px;
}
.lock__body {
  min-width: 0;
}
.lock__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.lock__title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lock__when {
  flex: none;
  font-size: 12px;
  color: #6b6b6b;
}
.lock__text {
  margin: 2px 0 0;
  font-size: 15px;
  line-height: 1.35;
  letter-spacing: -0.01em;
  color: #1c1c1e;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lock__hint {
  margin: 0;
  padding: 0 18px;
  font-size: 12.5px;
  line-height: 1.4;
  text-align: center;
  opacity: 0.72;
}
.lock__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
}
.lock__control {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(10px);
  display: grid;
  place-items: center;
}
.lock__control svg {
  width: 22px;
  height: 22px;
}
.lock__home {
  width: 120px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  align-self: flex-end;
  margin-bottom: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .lock__notification--new {
    animation: none;
  }
}
</style>
