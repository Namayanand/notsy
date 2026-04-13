package com.notsy.dto.request;

import lombok.Data;

@Data
public class UpdateNotebookRequest {
    private String title;
    private String description;
    private String colorTheme;
    private Boolean isPublic;
}
