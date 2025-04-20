package com.example.detectionapp;

import android.app.ProgressDialog;
import android.os.Bundle;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.example.detectionapp.databinding.ActivityMainBinding;
import com.google.android.gms.tasks.OnFailureListener;
import com.google.android.gms.tasks.OnSuccessListener;
import com.google.firebase.storage.FirebaseStorage;
import com.google.firebase.storage.StorageMetadata;
import com.google.firebase.storage.StorageReference;
import com.squareup.picasso.Picasso;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    ActivityMainBinding binding;
    StorageReference storageReference;
    ProgressDialog progressDialog;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        binding.ambilgambar.setOnClickListener(v -> {
            progressDialog = new ProgressDialog(MainActivity.this);
            progressDialog.setMessage("Mengambil Gambar...");
            progressDialog.setCancelable(false);
            progressDialog.show();

            String imageID = binding.namagambar.getText().toString().trim();

            if (imageID.isEmpty()) {
                Toast.makeText(MainActivity.this, "Masukkan nama gambar terlebih dahulu", Toast.LENGTH_SHORT).show();
                if (progressDialog.isShowing()) {
                    progressDialog.dismiss();
                }
                return; // Exit early if no input
            }

            // Initialize FirebaseStorage with custom bucket URL
            FirebaseStorage storage = FirebaseStorage.getInstance("gs://detection-app-f3849");

            // Reference to "Gambar/<imageID>.jpg" in bucket
            storageReference = storage.getReference("Gambar/" + imageID + ".jpg");

            // Get download URL and load with Picasso
            storageReference.getDownloadUrl()
                    .addOnSuccessListener(uri -> {
                        Picasso.get().load(uri).into(binding.gambarhasildeteksi);

                        // Now get metadata for upload time info:
                        storageReference.getMetadata()
                                .addOnSuccessListener(new OnSuccessListener<StorageMetadata>() {
                                    @Override
                                    public void onSuccess(StorageMetadata metadata) {
                                        long creationTimeMillis = metadata.getCreationTimeMillis();
                                        Date uploadDate = new Date(creationTimeMillis);

                                        SimpleDateFormat sdf =
                                                new SimpleDateFormat("dd MMM yyyy HH:mm:ss", Locale.getDefault());
                                        String formattedDate = sdf.format(uploadDate);

                                        binding.uploadTimeTextView.setText("Waktu Upload: " + formattedDate);

                                        if (progressDialog.isShowing()) {
                                            progressDialog.dismiss();
                                        }
                                    }
                                })
                                .addOnFailureListener(e -> {
                                    Toast.makeText(MainActivity.this,
                                            "Failed to retrieve upload time.", Toast.LENGTH_SHORT).show();

                                    binding.uploadTimeTextView.setText("Upload Time: -");

                                    if (progressDialog.isShowing()) {
                                        progressDialog.dismiss();
                                    }
                                });
                    })
                    .addOnFailureListener(e -> {
                        if (progressDialog.isShowing()) {
                            progressDialog.dismiss();
                        }

                        Toast.makeText(MainActivity.this, "Failed to retrieve gambar", Toast.LENGTH_SHORT).show();

                        e.printStackTrace();

                        binding.uploadTimeTextView.setText("Upload Time: -");
                    });
        });
    }
}
