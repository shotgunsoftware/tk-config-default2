// Copyright Epic Games, Inc. All Rights Reserved.

#include "EditorReimportManagerPythonAPIBPLibrary.h"


bool UEditorReimportHandlerPythonAPI::CanReimport(UObject* Obj)
{
	return FReimportManager::Instance()->CanReimport(Obj);
}

void UEditorReimportHandlerPythonAPI::UpdateReimportPath(UObject* Obj, const FString& Filename, int32 SourceFileIndex)
{
	FReimportManager::Instance()->UpdateReimportPath(Obj, Filename, SourceFileIndex);
}

bool UEditorReimportHandlerPythonAPI::Reimport(UObject* Obj, int32 SourceFileIndex)
{
	// Default arguments, except last one, `bAutomated`
	return FReimportManager::Instance()->Reimport(Obj, false, true, TEXT(""), nullptr, SourceFileIndex, false, true);
}

