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

var inventoryServiceURL string

type InventoryInfo struct {
	ProductID string `json:"productId"`
	Quantity  int    `json:"quantity"`
	Status    string `json:"status"`
	Warehouse string `json:"warehouse"`
}

func (i InventoryInfo) IsAvailable() bool {
	return i.Quantity > 0 && i.Status != "out_of_stock"
}

func (i InventoryInfo) StatusLabel() string {
	switch i.Status {
	case "in_stock":
		return "In stock"
	case "low_stock":
		return "Low stock"
	case "out_of_stock":
		return "Out of stock"
	default:
		return i.Status
	}
}

func init() {
	inventoryServiceURL = os.Getenv("INVENTORY_SERVICE_URL")
}

func isInventoryServiceConfigured() bool {
	return inventoryServiceURL != ""
}

func httpGetInventoryInfo(productID string) (*InventoryInfo, error) {
	url := inventoryServiceURL + "/inventory/" + productID
	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var inventoryInfo InventoryInfo
	if err := json.Unmarshal(responseBody, &inventoryInfo); err != nil {
		return nil, err
	}

	return &inventoryInfo, nil
}

func httpReserveInventory(productID string, quantity uint64) (*InventoryInfo, error) {
	return httpPostInventoryChange(productID, quantity, "reserve")
}

func httpReleaseInventory(productID string, quantity uint64) (*InventoryInfo, error) {
	return httpPostInventoryChange(productID, quantity, "release")
}

func httpPostInventoryChange(productID string, quantity uint64, action string) (*InventoryInfo, error) {
	url := inventoryServiceURL + "/inventory/" + productID + "/" + action
	payload, err := json.Marshal(map[string]uint64{"quantity": quantity})
	if err != nil {
		return nil, err
	}

	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Post(url, "application/json", bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("inventory %s failed with status %d: %s", action, resp.StatusCode, string(responseBody))
	}

	var inventoryInfo InventoryInfo
	if err := json.Unmarshal(responseBody, &inventoryInfo); err != nil {
		return nil, err
	}

	return &inventoryInfo, nil
}
