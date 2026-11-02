<script setup lang="ts">
import { computed } from 'vue'
import type { ExecutionEventItem, RunOut } from './types'
import { describeRunProgress } from './runProgress'

const props = defineProps<{
  run: RunOut | null
  events?: ExecutionEventItem[]
  syncDelayed?: boolean
  simulation?: boolean
}>()
const progress = computed(() => describeRunProgress(props.run, props.events))
</script>

<template>
  <section class="run-progress" aria-label="回答处理进度">
    <div class="run-progress-heading" role="status" aria-live="polite">
      <strong>{{ simulation ? '正在准备本地模拟回答' : progress.title }}</strong>
      <span>{{ simulation ? '模拟演示，不调用模型' : '按后端记录更新' }}</span>
    </div>
    <div
      class="run-progress-track"
      :class="{ 'is-active': progress.active || simulation, 'is-delayed': syncDelayed }"
      role="progressbar"
      :aria-label="simulation ? '本地模拟处理中' : progress.title"
      :aria-valuetext="simulation ? '本地模拟，未执行真实阶段' : (syncDelayed ? '进度更新暂时中断，尚未确认新状态' : progress.detail)"
    ><span></span></div>
    <ol v-if="!simulation" class="run-progress-steps">
      <li v-for="step in progress.steps" :key="step.id" :class="step.state"
        :aria-current="step.state === 'current' ? 'step' : undefined">
        {{ step.label }}<small v-if="step.state === 'skipped'">已跳过</small>
      </li>
    </ol>
    <p v-if="!simulation" class="run-progress-detail" role="status" aria-live="polite">
      {{ syncDelayed ? '进度更新暂时中断，正在等待连接恢复；尚未确认新的处理状态。' : progress.detail }}
    </p>
  </section>
</template>
