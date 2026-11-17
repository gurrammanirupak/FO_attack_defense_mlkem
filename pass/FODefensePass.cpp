#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

namespace {
struct FODefensePass : public PassInfoMixin<FODefensePass> {
    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        Instruction *TargetVerify = nullptr;
        for (auto &BB : F)
            for (auto &I : BB)
                if (auto *Call = dyn_cast<CallInst>(&I))
                    if (Function *Fn = Call->getCalledFunction())
                        if (Fn->getName().contains("verify")) { TargetVerify = &I; break; }
        if (!TargetVerify) return PreservedAnalyses::all();

        errs() << "[*] FODefensePass: Found FO Verify in " << F.getName() << "\n";

        Instruction *ClonedVerify = TargetVerify->clone();
        ClonedVerify->insertAfter(TargetVerify);

        IRBuilder<> Builder(ClonedVerify->getNextNode());
        Value *Cmp = Builder.CreateICmpNE(TargetVerify, ClonedVerify, "fault_detect");

        Instruction *SplitPt = cast<Instruction>(Cmp)->getNextNode();
        BasicBlock *CurrentBB = TargetVerify->getParent();
        BasicBlock *ContBB = CurrentBB->splitBasicBlock(SplitPt, "safe_cont");
        BasicBlock *TrapBB = BasicBlock::Create(F.getContext(), "fault_trap", &F);

        // native undefined-instruction trap: ud2 (x86) / udf (ARM) via llvm.trap
        Builder.SetInsertPoint(TrapBB);
        Builder.CreateIntrinsic(Intrinsic::trap, {}, {});
        Builder.CreateUnreachable();

        CurrentBB->getTerminator()->eraseFromParent();
        Builder.SetInsertPoint(CurrentBB);
        Builder.CreateCondBr(Cmp, TrapBB, ContBB);

        errs() << "[+] FODefensePass: Injected fault trap (llvm.trap) successfully.\n";
        return PreservedAnalyses::none();
    }
};
} // namespace

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return {LLVM_PLUGIN_API_VERSION, "FODefensePass", LLVM_VERSION_STRING,
        [](PassBuilder &PB) {
            PB.registerOptimizerLastEPCallback(                 // auto-fire so -fpass-plugin runs it
                [](ModulePassManager &MPM, OptimizationLevel) {
                    MPM.addPass(createModuleToFunctionPassAdaptor(FODefensePass()));
                });
            PB.registerPipelineParsingCallback(                 // also: opt -passes=fo-defense
                [](StringRef Name, FunctionPassManager &FPM, ArrayRef<PassBuilder::PipelineElement>) {
                    if (Name == "fo-defense") { FPM.addPass(FODefensePass()); return true; }
                    return false;
                });
        }};
}
