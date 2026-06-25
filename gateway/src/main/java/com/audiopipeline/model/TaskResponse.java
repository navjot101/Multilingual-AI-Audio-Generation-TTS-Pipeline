package com.audiopipeline.model;

public record TaskResponse(
    String taskId,
    String status,
    String pollUrl,
    String downloadUrl
) {}
