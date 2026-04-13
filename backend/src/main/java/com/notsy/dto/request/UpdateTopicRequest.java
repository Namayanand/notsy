package com.notsy.dto.request;

import lombok.Data;

@Data
public class UpdateTopicRequest {
    private String title;
    private String description;
    private Integer orderIndex;
    private java.util.List<String> tags;
}
