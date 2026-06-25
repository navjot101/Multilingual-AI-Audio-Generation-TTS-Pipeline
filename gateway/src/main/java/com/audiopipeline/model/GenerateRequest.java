package com.audiopipeline.model;

import jakarta.validation.constraints.NotBlank;

public record GenerateRequest(
    @NotBlank String script,
    String genre,
    String language
) {
    public GenerateRequest {
        if (genre == null) genre = "general";
        if (language == null) language = "en";
    }
}
