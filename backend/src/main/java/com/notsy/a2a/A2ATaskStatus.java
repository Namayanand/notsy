package com.notsy.a2a;

/**
 * Task status enum matching A2A protocol specification
 */
public enum A2ATaskStatus {
    SUBMITTED("submitted"),
    WORKING("working"),
    COMPLETED("completed"),
    FAILED("failed");

    private final String value;

    A2ATaskStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static A2ATaskStatus fromValue(String value) {
        for (A2ATaskStatus status : A2ATaskStatus.values()) {
            if (status.value.equalsIgnoreCase(value)) {
                return status;
            }
        }
        return SUBMITTED;
    }
}