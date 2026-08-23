#!/bin/sh
# Shared by both bootstrap Jobs (secret-decrypt-job.yaml, instance-apply-job.yaml).
# Polls a check command until it succeeds, then runs an action command once.
# Bounded by activeDeadlineSeconds on the Job itself, not by this script —
# Kubernetes kills the pod (Job goes Failed) if the deadline passes while
# this loop is still polling.
set -eu

CHECK="$1"
ACTION="$2"

until eval "$CHECK"; do
  echo "waiting: $CHECK"
  sleep 10
done

eval "$ACTION"
