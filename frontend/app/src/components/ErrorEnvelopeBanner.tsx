import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { ApiErrorResponse } from '../types/api';
import { Colors } from '../theme/colors';

interface ErrorEnvelopeBannerProps {
  message: string;
  errorEnvelope?: ApiErrorResponse | null;
  onDismiss: () => void;
}

/**
 * Dismissable error banner shown at the top of the screen when an API call fails.
 * Directly mirrors the Kotlin ErrorEnvelopeBanner component with structured
 * error code, timestamp, and human-readable message.
 */
export function ErrorEnvelopeBanner({
  message,
  errorEnvelope,
  onDismiss,
}: ErrorEnvelopeBannerProps) {
  const isApiError = errorEnvelope !== null && errorEnvelope !== undefined;
  const headerText = isApiError ? `API ERROR: ${errorEnvelope.error_code}` : 'SYSTEM ERROR';

  return (
    <View style={styles.container}>
      <View style={styles.contentColumn}>
        <Text style={styles.header}>{headerText}</Text>
        <Text style={styles.message}>{message}</Text>
        {errorEnvelope?.timestamp && (
          <Text style={styles.timestamp}>Timestamp: {errorEnvelope.timestamp}</Text>
        )}
      </View>
      <TouchableOpacity
        onPress={onDismiss}
        style={styles.dismissBtn}
        accessibilityLabel="Dismiss error"
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.dismissText}>✕</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#421010',
    borderColor: '#FF5252',
    borderWidth: 1,
    borderRadius: 8,
    marginHorizontal: 12,
    marginVertical: 6,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  contentColumn: {
    flex: 1,
    gap: 2,
  },
  header: {
    color: '#FF8A80',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  message: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 16,
  },
  timestamp: {
    color: '#EF9A9A',
    fontSize: 9,
    marginTop: 2,
  },
  dismissBtn: {
    padding: 4,
  },
  dismissText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
