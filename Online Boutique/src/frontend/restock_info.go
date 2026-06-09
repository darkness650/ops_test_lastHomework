// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

var restockServiceURL string
var restockAPIToken string

func init() {
	restockServiceURL = os.Getenv("RESTOCK_SERVICE_URL")
	restockAPIToken = envOrDefault("RESTOCK_API_TOKEN", "online-boutique-restock")
}

func isRestockServiceConfigured() bool {
	return restockServiceURL != ""
}

func httpRestockProduct(productID string, quantity uint64) error {
	url := restockServiceURL + "/restock/" + productID
	payload, err := json.Marshal(map[string]uint64{"quantity": quantity})
	if err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+restockAPIToken)

	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("restock failed with status %d: %s", resp.StatusCode, string(responseBody))
	}

	return nil
}
