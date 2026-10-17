"""P06-A3 training provenance, surrogate fitting and tamper detection."""
from __future__ import annotations

import copy
import json

import pytest

torch = pytest.importorskip("torch")
from torch.utils.data import DataLoader, TensorDataset

from loihi_twin_v2.p06_a3_training import (
    HIDDEN_LIF, OUTPUT_LIF, MIN_VALIDATION_ACCURACY, TRAINING_SCHEMA,
    TrainSettings, evaluate, initialize_model, integer_weights_sha256,
    load_candidate, save_candidate, train_epoch,
)


def _synthetic_loader():
    images = torch.zeros((6,784),dtype=torch.uint8)
    images[0,:50] = 255
    images[1,50:100] = 255
    images[2,100:150] = 255
    images[3,:150] = 255
    images[4,100:130] = 128
    images[5,30:180] = 200
    targets = torch.tensor([0,1,2,0,2,1],dtype=torch.long)
    return DataLoader(TensorDataset(images,targets),batch_size=3,shuffle=False)


def test_predeclared_profile_and_model_initializer_determinism():
    assert MIN_VALIDATION_ACCURACY == 0.60
    assert HIDDEN_LIF.threshold == 32 and OUTPUT_LIF.threshold == 8
    settings = TrainSettings()
    a,b = initialize_model(settings),initialize_model(settings)
    assert torch.equal(a.w_input_hidden,b.w_input_hidden)
    assert torch.equal(a.w_hidden_output,b.w_hidden_output)
    assert a.w_input_hidden.abs().sum() > 0
    assert a.w_hidden_output.abs().sum() > 0
    assert integer_weights_sha256(a) == integer_weights_sha256(b)
    c = initialize_model(TrainSettings(seed=settings.seed+1))
    assert integer_weights_sha256(a) != integer_weights_sha256(c)


def test_synthetic_train_epoch_and_validation_dont_access_mnist():
    model=initialize_model(TrainSettings())
    loader=_synthetic_loader()
    with torch.no_grad():
        before=model(next(iter(loader))[0]).clone()
    optimizer=torch.optim.Adam(model.parameters(),lr=0.05)
    tr=train_epoch(model,loader,optimizer)
    val=evaluate(model,loader)
    with torch.no_grad():
        after=model(next(iter(loader))[0])
    assert before.shape == after.shape == (3,10)
    assert (tr['count'],val['count'])==(6,6)
    assert 0 <= tr['accuracy'] <= 1 and 0 <= val['accuracy'] <= 1
    assert 0 <= val['all_silent_fraction'] <= 1
    assert len(val["predicted_class_histogram"]) == 10
    assert sum(val["predicted_class_histogram"]) == val["count"]
    assert len(val["output_spike_counts_by_class"]) == 10
    assert val["mean_output_spikes_per_image"] == pytest.approx(sum(val["output_spike_counts_by_class"]) / val["count"])
    assert torch.equal(after,after.round())
    assert torch.isfinite(model.w_input_hidden).all()
    assert torch.isfinite(model.w_hidden_output).all()


def test_candidate_state_and_sha_can_be_reloaded_with_metadata(tmp_path):
    model=initialize_model(TrainSettings())
    settings=TrainSettings(epochs=1,batch_size=3)
    val={'accuracy':0.95,'count':6,'mean_cross_entropy':0.5,'all_silent_count':0,'all_silent_fraction':0.0}
    history=[{'epoch':1,'train':{'accuracy':0.4},'validation':val}]
    folder=tmp_path/'fixture_candidate'
    manifest=save_candidate(model,folder,settings,
        {'schema':'synthetic-idx-test-not-benchmark',
         'official_test_set':'sealed'},history,1)
    assert manifest['schema'] == TRAINING_SCHEMA
    assert manifest['candidate_go'] is False # cannot claim MNIST GO from fake data
    assert manifest['official_mnist_test_status'] == 'SEALED / NOT READ'
    assert manifest['weights_file_sha256'] and manifest['exported_integer_weights_sha256']
    restored,loaded=load_candidate(folder)
    assert loaded==manifest
    assert restored.hidden_config == HIDDEN_LIF and restored.output_config == OUTPUT_LIF
    assert integer_weights_sha256(restored)==integer_weights_sha256(model)
    assert torch.equal(restored.w_input_hidden,model.w_input_hidden)
    assert torch.equal(restored.w_hidden_output,model.w_hidden_output)
    with pytest.raises(FileExistsError):
        save_candidate(model,folder,settings,{'schema':'fake'},history,1)


def test_candidate_tampering_is_rejected(tmp_path):
    model=initialize_model(TrainSettings())
    val={'accuracy':0.6,'count':1}
    out=tmp_path/'candidate'
    save_candidate(model,out,TrainSettings(epochs=1),{'schema':'synthetic'},[{'validation':val}],1)
    chk=out/'weights_state_dict.pt'
    original=chk.read_bytes()
    chk.write_bytes(original+b'x')
    with pytest.raises(ValueError,match='hash mismatch'):
        load_candidate(out)
    chk.write_bytes(original)
    manifest=json.loads((out/'candidate_manifest.json').read_text())
    manifest['neuron_config']['hidden']['threshold'] = 9000
    (out/'candidate_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='neuron contract'):
        load_candidate(out)


@pytest.mark.parametrize('invalid',[
    {'epochs':0},{'batch_size':0},{'learning_rate':0},
    {'surrogate_width':float('nan')},{'seed':True},
])
def test_bad_training_configuration_fails_closed(invalid):
    with pytest.raises(ValueError):
        TrainSettings(**invalid)


def test_no_saved_candidate_without_validated_epoch(tmp_path):
    model=initialize_model(TrainSettings())
    with pytest.raises(ValueError,match='without completed validation'):
        save_candidate(model,tmp_path/'not_saved',TrainSettings(),{},[],0)
    assert not (tmp_path/'not_saved').exists()
